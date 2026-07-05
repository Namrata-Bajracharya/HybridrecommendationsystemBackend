"""
Hybrid Recommendation Engine Service
Integrates collaborative filtering + content-based recommendations + user similarity
"""
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.logger import logger

# ML model imports (try to import, fallback if not available)
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not installed - recommendation model serialization disabled")

# Module-level storage shared across all RecommendationService instances
# (FastAPI creates a new service per request, so instance attrs don't persist)
_user_actions: Dict[str, Dict[str, str]] = {}
_global_action_scores: Dict[str, float] = {}


class RecommendationService:
    """
    Hybrid recommendation engine combining:
    - Content-based filtering (product features)
    - Collaborative filtering (user behavior)
    - User similarity (buying patterns)
    """

    def __init__(self, db: Session):
        self.db = db
        self.ml_data_path = Path(__file__).parent.parent.parent / "ml" / "data" / "combined"
        self.model = None
        self.recommendation_cache = {}
        self.user_similarity_cache = {}
        # user_actions and global_action_scores are module-level shared dicts

        self._load_ml_data()
        self._load_paraquest_scores()
        self._load_trained_model()

    def _load_ml_data(self):
        """Load preprocessed datasets from ML pipeline"""
        try:
            if not self.ml_data_path.exists():
                logger.warning(f"ML data path not found: {self.ml_data_path}")
                self.items_df = pd.DataFrame()
                self.interactions_df = pd.DataFrame()
                self.content_features = pd.DataFrame()
                return

            # Load combined datasets
            items_file = self.ml_data_path / "combined_items.parquet"
            interactions_file = self.ml_data_path / "combined_interactions.parquet"
            features_file = self.ml_data_path / "hm_content_features.parquet"

            if items_file.exists():
                self.items_df = pd.read_parquet(items_file)
                logger.info(f"Loaded {len(self.items_df)} items")
            else:
                self.items_df = pd.DataFrame()

            if interactions_file.exists():
                self.interactions_df = pd.read_parquet(interactions_file)
                logger.info(f"Loaded {len(self.interactions_df)} interactions")
            else:
                self.interactions_df = pd.DataFrame()

            if features_file.exists():
                self.content_features = pd.read_parquet(features_file)
                logger.info(f"Loaded content features for {len(self.content_features)} items")
            else:
                self.content_features = pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading ML data: {e}")
            self.items_df = pd.DataFrame()
            self.interactions_df = pd.DataFrame()
            self.content_features = pd.DataFrame()

    def _load_trained_model(self):
        """Load pre-trained XGBoost/LightGBM model"""
        try:
            if not JOBLIB_AVAILABLE:
                logger.warning("joblib not available - using fallback recommendation method")
                return

            model_path = self.ml_data_path / "hybrid_ranker_model.joblib"
            if model_path.exists():
                self.model = joblib.load(model_path)
                logger.info("Loaded trained hybrid ranker model")
            else:
                logger.warning(f"Trained model not found at {model_path}")

        except Exception as e:
            logger.error(f"Error loading trained model: {e}")
            self.model = None

    def _load_paraquest_scores(self):
        """Attempt to load precomputed Paraquest scores (parquet)
        Expected format: columns ['user_id', 'item_id', 'score']
        """
        self.paraquest_scores = None
        try:
            pq_file = self.ml_data_path / "paraquest_scores.parquet"
            if pq_file.exists():
                self.paraquest_scores = pd.read_parquet(pq_file)
                logger.info(f"Loaded Paraquest scores: {len(self.paraquest_scores)} rows")
                return

            # Fallback: some ML pipelines store user-item predicted scores in
            # `hybrid_features_selected.parquet` or `hybrid_features.parquet`.
            fallback_files = [
                self.ml_data_path / "hybrid_features_selected.parquet",
                self.ml_data_path / "hybrid_features.parquet",
            ]

            for f in fallback_files:
                if f.exists():
                    df = pd.read_parquet(f)
                    # Expect user-item predictions or features; try to detect columns
                    if {"user_id", "item_id"}.issubset(df.columns):
                        # Find a numeric column to use as score (exclude ids)
                        numeric_cols = [c for c in df.select_dtypes(include=["number"]).columns if c not in ("user_id", "item_id")]
                        if numeric_cols:
                            score_col = numeric_cols[0]
                            self.paraquest_scores = df[["user_id", "item_id", score_col]].rename(columns={score_col: "score"})
                            logger.info(f"Loaded Paraquest-like scores from {f} using column {score_col}: {len(self.paraquest_scores)} rows")
                            return

            # Not strictly an error — Paraquest may not have been run or outputs unavailable
            logger.debug(f"Paraquest scores not found at {pq_file} or fallback feature files")

        except Exception as e:
            logger.error(f"Error loading Paraquest scores: {e}")
            self.paraquest_scores = None

    def _get_para_score(self, user_id: str, item_id: str) -> Optional[float]:
        """Lookup Paraquest score for (user_id, item_id) if available"""
        try:
            if self.paraquest_scores is None or self.paraquest_scores.empty:
                return None

            row = self.paraquest_scores[
                (self.paraquest_scores["user_id"] == user_id)
                & (self.paraquest_scores["item_id"] == item_id)
            ]

            if row.empty:
                return None

            return float(row.iloc[0]["score"])
        except Exception:
            return None

    def get_recommendations_for_user(
        self,
        user_id: str,
        top_k: int = 10,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Generate recommendations for a user based on their history
        Uses: user activity, item popularity, content similarity
        """
        if exclude_ids is None:
            exclude_ids = []

        try:
            # Get user's interaction history
            user_history = self._get_user_history(user_id)
            logger.info(f"User {user_id} history: {len(user_history)} items")

            # Generate candidates (popular items + random items)
            candidates = self._generate_candidates(
                user_id=user_id,
                exclude_ids=exclude_ids + list(user_history),
                top_k=top_k * 5,  # Get more candidates for ranking
            )

            if not candidates:
                logger.warning(f"No candidates generated for user {user_id}")
                return []

            # Rank candidates
            ranked_items = self._rank_candidates(
                user_id=user_id,
                candidates=candidates,
                user_history=user_history,
            )

            # Return top K
            recommendations = []
            for rank, (item_id, score) in enumerate(ranked_items[:top_k], 1):
                recommendations.append(
                    {
                        "item_id": item_id,
                        "rank": rank,
                        "score": float(score),
                        "reason": "User preferences",
                    }
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}")
            return []

    def get_similar_products(
        self,
        product_id: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Get products similar to the given product
        Uses: content-based similarity + user who bought this also bought that
        """
        try:
            similar_items = []

            # 1. Content-based similarity
            if not self.content_features.empty:
                content_similar = self._get_content_similar(product_id, top_k)
                similar_items.extend(content_similar)

            # 2. Collaborative similarity (people who bought X also bought Y)
            collab_similar = self._get_collaborative_similar(product_id, top_k)
            similar_items.extend(collab_similar)

            # Deduplicate and sort by score
            seen = set()
            ranked = []
            for item in similar_items:
                if item["item_id"] not in seen:
                    seen.add(item["item_id"])
                    ranked.append(item)

            # Sort by score descending
            ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

            return ranked[:top_k]

        except Exception as e:
            logger.error(f"Error getting similar products for {product_id}: {e}")
            return []

    def get_cart_recommendations(
        self,
        user_id: str,
        cart_items: List[str],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Get recommendations based on items in user's cart
        Combines recommendations for each cart item
        """
        try:
            if not cart_items:
                return []

            all_recommendations = {}

            # Get recommendations for each cart item
            for item_id in cart_items:
                similar = self._get_collaborative_similar(item_id, top_k=3)
                for rec in similar:
                    item = rec["item_id"]
                    if item not in cart_items:  # Don't recommend items already in cart
                        if item not in all_recommendations:
                            all_recommendations[item] = 0
                        all_recommendations[item] += rec.get("score", 0.5)

            # Sort by score and return top K
            sorted_recs = sorted(
                all_recommendations.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            recommendations = []
            for rank, (item_id, score) in enumerate(sorted_recs[:top_k], 1):
                recommendations.append(
                    {
                        "item_id": item_id,
                        "rank": rank,
                        "score": float(score),
                        "reason": f"People who bought items in your cart also bought this",
                    }
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating cart recommendations: {e}")
            return []

    def get_similar_user_recommendations(
        self,
        user_id: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """
        Find users with similar buying patterns and recommend their purchases
        Hybrid collaborative filtering approach
        """
        try:
            # Get user's purchase history
            user_history = self._get_user_history(user_id)

            if not user_history:
                logger.warning(f"User {user_id} has no purchase history")
                return []

            # Find similar users
            similar_users = self._find_similar_users(user_id, user_history, top_k=5)

            if not similar_users:
                logger.warning(f"No similar users found for {user_id}")
                return []

            # Get items purchased by similar users but not by current user
            recommendations = {}

            for sim_user_id, similarity_score in similar_users:
                sim_user_history = self._get_user_history(sim_user_id)

                # Items purchased by similar user but not by current user
                new_items = [
                    item for item in sim_user_history
                    if item not in user_history
                ]

                for item_id in new_items:
                    if item_id not in recommendations:
                        recommendations[item_id] = 0
                    recommendations[item_id] += similarity_score

            # Sort and return top K
            sorted_recs = sorted(
                recommendations.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            result = []
            for rank, (item_id, score) in enumerate(sorted_recs[:top_k], 1):
                result.append(
                    {
                        "item_id": item_id,
                        "rank": rank,
                        "score": float(score),
                        "reason": "Based on users with similar taste",
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error generating similar user recommendations: {e}")
            return []

    def get_review_based_recommendations(
        self,
        user_id: str,
        product_id: str,
        rating: int,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Recommend products based on user's review/rating
        If user rates highly, recommend similar products
        """
        try:
            if rating >= 4:  # High rating - recommend similar products
                similar = self.get_similar_products(product_id, top_k)

                # Add context to recommendations
                for rec in similar:
                    rec["reason"] = f"Similar to product you rated {rating} stars"

                return similar
            else:
                # Low rating - recommend alternative products
                return self.get_recommendations_for_user(
                    user_id=user_id,
                    top_k=top_k,
                    exclude_ids=[product_id],
                )

        except Exception as e:
            logger.error(f"Error generating review-based recommendations: {e}")
            return []

    # ===== PRIVATE HELPER METHODS =====

    def _get_user_history(self, user_id: str) -> Set[str]:
        """Get set of items user has interacted with"""
        if self.interactions_df.empty:
            return set()

        user_interactions = self.interactions_df[
            self.interactions_df["user_id"] == user_id
        ]["item_id"].unique()

        return set(user_interactions)

    def _generate_candidates(
        self,
        user_id: str,
        exclude_ids: List[str],
        top_k: int = 50,
    ) -> List[str]:
        """Generate candidate items for ranking"""
        if self.items_df.empty:
            return []

        exclude_set = set(exclude_ids)
        all_items = self.items_df["item_id"].values

        # Get popular items
        if not self.interactions_df.empty:
            item_popularity = self.interactions_df["item_id"].value_counts()
            popular_items = item_popularity.head(100).index.tolist()
        else:
            popular_items = []

        # Random sampling
        np.random.seed(42 + hash(user_id) % 10000)  # Deterministic but user-specific
        random_items = list(np.random.choice(all_items, size=min(100, len(all_items))))

        # Combine and filter
        candidates = []
        seen = set()

        for item in popular_items + random_items:
            if item not in exclude_set and item not in seen:
                candidates.append(item)
                seen.add(item)

        return candidates[:top_k]

    def _rank_candidates(
        self,
        user_id: str,
        candidates: List[str],
        user_history: Set[str],
    ) -> List[Tuple[str, float]]:
        """
        Rank candidates using ML model or heuristic scoring
        Returns: [(item_id, score), ...]
        """
        if not candidates:
            return []

        scored_items = []

        for item_id in candidates:
            # Heuristic / fallback score
            heuristic_score = self._compute_item_score(
                user_id=user_id,
                item_id=item_id,
                user_history=user_history,
            )

            # Paraquest model score (if precomputed)
            para_score = self._get_para_score(user_id, item_id)

            if para_score is not None:
                # Combine scores: give Paraquest higher weight when available
                combined = 0.6 * float(para_score) + 0.4 * float(heuristic_score)
            else:
                combined = float(heuristic_score)

            scored_items.append((item_id, combined))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        return scored_items

    def _compute_item_score(
        self,
        user_id: str,
        item_id: str,
        user_history: Set[str],
    ) -> float:
        """
        Compute recommendation score for an item
        Combines multiple signals: popularity, content similarity, user activity
        """
        score = 0.0

        # 1. Item popularity
        if not self.interactions_df.empty:
            item_count = len(
                self.interactions_df[self.interactions_df["item_id"] == item_id]
            )
            popularity_score = min(item_count / 1000, 1.0)  # Normalize
            score += popularity_score * 0.3

        # 2. Content similarity
        if not self.content_features.empty:
            content_score = self.content_features[
                self.content_features["item_id"] == item_id
            ]["content_similarity_score"].values

            if len(content_score) > 0:
                score += float(content_score[0]) * 0.2

        # 3. User activity (user interaction frequency)
        if not self.interactions_df.empty:
            user_count = len(
                self.interactions_df[self.interactions_df["user_id"] == user_id]
            )
            user_activity_score = min(user_count / 1000, 1.0)
            score += user_activity_score * 0.2

        # 4. Base score
        score += 0.3

        return min(score, 1.0)  # Clamp to [0, 1]

    def _get_content_similar(
        self,
        product_id: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """Get products similar by content"""
        if self.content_features.empty:
            return []

        try:
            # For now, return top-rated items as "similar" (placeholder)
            similar_items = []

            all_items = self.content_features[
                self.content_features["item_id"] != product_id
            ].head(top_k)

            for _, row in all_items.iterrows():
                similar_items.append(
                    {
                        "item_id": row["item_id"],
                        "score": float(row.get("content_similarity_score", 0.5)),
                        "reason": "Similar product",
                    }
                )

            return similar_items

        except Exception as e:
            logger.error(f"Error getting content similar products: {e}")
            return []

    def _get_collaborative_similar(
        self,
        product_id: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """Get products: 'people who bought X also bought Y'"""
        if self.interactions_df.empty:
            return []

        try:
            # Users who bought the target product
            users_bought_target = set(
                self.interactions_df[
                    self.interactions_df["item_id"] == product_id
                ]["user_id"].unique()
            )

            if not users_bought_target:
                return []

            # Items these users also bought
            other_items = self.interactions_df[
                (self.interactions_df["user_id"].isin(users_bought_target))
                & (self.interactions_df["item_id"] != product_id)
            ]["item_id"].value_counts()

            similar_items = []
            for item_id, count in other_items.head(top_k).items():
                # Normalize count to score [0, 1]
                score = min(count / max(len(users_bought_target), 1), 1.0)
                similar_items.append(
                    {
                        "item_id": item_id,
                        "score": float(score),
                        "reason": f"People who bought this also bought that",
                    }
                )

            return similar_items

        except Exception as e:
            logger.error(f"Error getting collaborative similar products: {e}")
            return []

    def _find_similar_users(
        self,
        user_id: str,
        user_history: Set[str],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find users with similar purchase patterns
        Returns: [(similar_user_id, similarity_score), ...]
        """
        if self.interactions_df.empty:
            return []

        try:
            similar_users = []

            # Get all unique users
            all_users = self.interactions_df["user_id"].unique()

            for other_user in all_users:
                if other_user == user_id:
                    continue

                other_history = set(
                    self.interactions_df[
                        self.interactions_df["user_id"] == other_user
                    ]["item_id"].unique()
                )

                # Jaccard similarity
                intersection = len(user_history & other_history)
                union = len(user_history | other_history)

                if union > 0:
                    similarity = intersection / union
                    if similarity > 0:
                        similar_users.append((other_user, similarity))

            # Sort by similarity and return top K
            similar_users.sort(key=lambda x: x[1], reverse=True)

            return similar_users[:top_k]

        except Exception as e:
            logger.error(f"Error finding similar users: {e}")
            return []

    # ── Test Recommendation helpers (in-memory user actions) ──

    ACTION_WEIGHTS = {
        "buy": 1.0,
        "return": -1.0,
        "positive_review": 0.8,
        "negative_review": -0.8,
        "high_rating": 0.6,
        "low_rating": -0.6,
        "cancel": 0.0,
        "normal": 0.0,
    }

    def record_action(self, user_id: str, product_id: str, action: str):
        """Record a buy/cancel/return/review/rating action for a user (for test recommendation).
        Also updates global_action_scores so auth user actions affect ALL users' recommendations."""
        if user_id not in _user_actions:
            _user_actions[user_id] = {}

        # Undo previous action's global score if user had one
        prev_action = _user_actions[user_id].get(product_id)
        if prev_action and prev_action != action:
            prev_weight = self.ACTION_WEIGHTS.get(prev_action, 0)
            _global_action_scores[product_id] = _global_action_scores.get(product_id, 0) - prev_weight

        if action == "normal":
            _user_actions[user_id].pop(product_id, None)
        else:
            _user_actions[user_id][product_id] = action
            new_weight = self.ACTION_WEIGHTS.get(action, 0)
            _global_action_scores[product_id] = _global_action_scores.get(product_id, 0) + new_weight

        # Cleanup zero entries
        if _global_action_scores.get(product_id) == 0:
            _global_action_scores.pop(product_id, None)

        logger.info(f"User {user_id} action {action} on product {product_id}")

    def get_user_actions(self, user_id: str) -> Dict[str, str]:
        """Get all actions for a user"""
        return _user_actions.get(user_id, {})

    def get_test_recommendations(
        self,
        user_id: str,
        top_k: int = 10,
        cart_item_ids: Optional[List[str]] = None,
        viewed_product_ids: Optional[List[str]] = None,
        wishlist_item_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Hybrid recommendation combining multiple factors:

        A. User reviews — products similar to highly-rated items (auth only)
        B. Product popularity — most-interacted items across all users
        C. Wishlist — products similar to wishlist items (from DB for auth, from params for guests)
        D. Similar-user purchases — users with matching buying patterns (auth only)
        E. Real-time user actions — buy/return/review/rating signals (auth only)
        F. Cart-based — recommendations from items in user's cart
        G. Viewed-products — recommendations based on recently viewed items + category affinity
        H. Category-based — from frequently viewed categories
        I. Guest wishlist — wishlist items sent from browser storage
        """
        from app.models.review import Review
        from app.models.wishlist import Wishlist
        from app.models.order_item import OrderItem
        from app.models.product import Product

        if cart_item_ids is None:
            cart_item_ids = []
        if viewed_product_ids is None:
            viewed_product_ids = []
        if wishlist_item_ids is None:
            wishlist_item_ids = []

        scores: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}

        def _add_score(pid: str, weight: float, reason: str):
            scores[pid] = scores.get(pid, 0.0) + weight
            if pid not in reasons:
                reasons[pid] = []
            reasons[pid].append(reason)

        try:
            uid = int(user_id) if user_id != "anon" else None
        except ValueError:
            uid = None

        is_auth = uid is not None

        # ── A. Review-based (auth only) ──
        if is_auth:
            high_rated = (
                self.db.query(Review.product_id)
                .filter(Review.user_id == uid, Review.rating >= 4)
                .all()
            )
            for (pid,) in high_rated:
                similar = self.get_similar_products(str(pid), top_k=3)
                for rec in similar:
                    _add_score(rec["item_id"], 0.25, "Based on your high-rated items")

        # ── B. Popularity ──
        if not self.interactions_df.empty:
            pop = self.interactions_df["item_id"].value_counts().head(20)
            for item_id, count in pop.items():
                norm = min(count / 1000, 1.0)
                _add_score(str(item_id), norm * 0.2, "Popular product")
        else:
            try:
                pop_items = (
                    self.db.query(OrderItem.product_id)
                    .group_by(OrderItem.product_id)
                    .order_by(func.count(OrderItem.product_id).desc())
                    .limit(20)
                    .all()
                )
                for i, (pid,) in enumerate(pop_items):
                    norm = max(0, 1 - i / 20)
                    _add_score(str(pid), norm * 0.2, "Popular product")
            except Exception:
                pass

        def _db_similar_products(pid: str, top_k: int = 3) -> List[Dict]:
            """Fallback: find products in the same category via DB (works without ML data)"""
            try:
                product = self.db.query(Product.category_id).filter(Product.id == int(pid)).first()
                if not product:
                    return []
                similar = (
                    self.db.query(Product.id)
                    .filter(
                        Product.category_id == product.category_id,
                        Product.id != int(pid),
                        Product.is_active == True,
                    )
                    .limit(top_k)
                    .all()
                )
                return [{"item_id": str(sid)} for (sid,) in similar]
            except Exception:
                return []

        # ── C. Wishlist-based (auth: from DB, guest: from params) ──
        wish_ids = []
        if is_auth:
            db_wishlist = (
                self.db.query(Wishlist.product_id)
                .filter(Wishlist.user_id == uid)
                .all()
            )
            wish_ids = [str(pid) for (pid,) in db_wishlist]
        wish_ids = list(set(wish_ids + wishlist_item_ids))
        for wid in wish_ids:
            similar = self.get_similar_products(wid, top_k=3)
            if not similar:
                similar = _db_similar_products(wid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], 0.25, "Similar to your wishlist items")

        # ── D. Similar-user purchases (auth only) ──
        if is_auth:
            sim_user_recs = self.get_similar_user_recommendations(user_id=user_id, top_k=top_k)
            for rec in sim_user_recs:
                _add_score(rec["item_id"], 0.3, rec.get("reason", "Users with similar taste bought this"))

        # ── E. Real-time user actions (auth only) ──
        actions = _user_actions.get(user_id, {})

        # Buy: similar products get a strong positive boost
        bought_ids = [pid for pid, act in actions.items() if act == "buy"]
        for pid in bought_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], 0.4, "Based on your current purchases")

        # Return: similar products get a negative signal
        return_ids = [pid for pid, act in actions.items() if act == "return"]
        for pid in return_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], -0.3, "You returned similar items")

        # Positive review: similar products get a boost
        pos_review_ids = [pid for pid, act in actions.items() if act == "positive_review"]
        for pid in pos_review_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], 0.3, "Based on your positive reviews")

        # Negative review: similar products get penalized
        neg_review_ids = [pid for pid, act in actions.items() if act == "negative_review"]
        for pid in neg_review_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], -0.3, "Based on your negative reviews")

        # High rating: similar products get a moderate boost
        high_rating_ids = [pid for pid, act in actions.items() if act == "high_rating"]
        for pid in high_rating_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], 0.25, "Based on your high ratings")

        # Low rating: similar products get a moderate penalty
        low_rating_ids = [pid for pid, act in actions.items() if act == "low_rating"]
        for pid in low_rating_ids:
            similar = self.get_similar_products(pid, top_k=3)
            if not similar:
                similar = _db_similar_products(pid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], -0.25, "Based on your low ratings")

        # ── J. Global test actions from all auth users (applies to ALL users) ──
        for pid, global_score in _global_action_scores.items():
            if global_score > 0:
                similar = self.get_similar_products(pid, top_k=2)
                if not similar:
                    similar = _db_similar_products(pid, top_k=2)
                for rec in similar:
                    _add_score(rec["item_id"], min(global_score * 0.05, 0.2), "Popular with other testers")
            elif global_score < 0:
                similar = self.get_similar_products(pid, top_k=2)
                if not similar:
                    similar = _db_similar_products(pid, top_k=2)
                for rec in similar:
                    _add_score(rec["item_id"], max(global_score * 0.05, -0.2), "Less popular with other testers")

        # ── F. Cart-based ──
        for cid in cart_item_ids:
            similar = self.get_similar_products(cid, top_k=3)
            if not similar:
                similar = _db_similar_products(cid, top_k=3)
            for rec in similar:
                _add_score(rec["item_id"], 0.3, "Based on items in your cart")

        # ── G. Viewed-products-based (recently viewed) ──
        for vid in viewed_product_ids:
            similar = self.get_similar_products(vid, top_k=2)
            if not similar:
                similar = _db_similar_products(vid, top_k=2)
            for rec in similar:
                _add_score(rec["item_id"], 0.2, "Similar to products you viewed")

        # ── H. Category-based from viewed products (DB fallback) ──
        if viewed_product_ids:
            try:
                viewed_cats = set()
                for vid in viewed_product_ids:
                    product = self.db.query(Product.category_id).filter(Product.id == int(vid)).first()
                    if product:
                        viewed_cats.add(product.category_id)

                if viewed_cats:
                    same_cat = (
                        self.db.query(Product.id)
                        .filter(
                            Product.category_id.in_(list(viewed_cats)),
                            ~Product.id.in_([int(v) for v in viewed_product_ids if v.isdigit()]),
                            Product.is_active == True,
                        )
                        .limit(15)
                        .all()
                    )
                    for (sid,) in same_cat:
                        _add_score(str(sid), 0.15, "From categories you browse")
            except Exception:
                pass

        # Exclude products the user has cancelled, bought, or returned
        exclude = set()
        for pid, act in actions.items():
            if act in ("cancel", "buy", "return"):
                exclude.add(pid)

        # Sort and return top K
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        seen = set()
        for pid, score in ranked:
            if pid in exclude or pid in seen:
                continue
            seen.add(pid)
            results.append({
                "item_id": pid,
                "rank": len(results) + 1,
                "score": min(score, 1.0),
                "reasons": reasons.get(pid, []),
                "reason": reasons.get(pid, ["Personalized for you"])[0],
            })
            if len(results) >= top_k:
                break

        return results

    def clear_cache(self):
        """Clear recommendation caches"""
        self.recommendation_cache.clear()
        self.user_similarity_cache.clear()
        logger.info("Recommendation caches cleared")
