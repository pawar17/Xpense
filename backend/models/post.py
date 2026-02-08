from datetime import datetime
from bson import ObjectId

class Post:
    def __init__(self, db):
        self.collection = db.posts
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes for better query performance"""
        self.collection.create_index("user_id")
        self.collection.create_index([("created_at", -1)])
        self.collection.create_index([("type", 1), ("created_at", -1)])

    def create_post(self, user_id, content, post_type="update", visibility="public", metadata=None):
        """
        Create a new post

        Args:
            user_id: User creating the post
            content: Post text content
            post_type: Type of post (update, milestone, achievement, level-up, goal-completed)
            visibility: public, friends-only, private
            metadata: Additional data (goal_id, level, etc.)
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        post = {
            "user_id": user_id,
            "content": content,
            "type": post_type,
            "visibility": visibility,
            "metadata": metadata or {},
            "likes": [],  # Array of user_ids who liked
            "comments": [],  # Array of comment objects
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(post)
        return result.inserted_id

    def get_feed(self, user_id, limit=50, skip=0, feed_type="all"):
        """
        Get posts for user's feed

        Args:
            user_id: Current user viewing the feed
            limit: Number of posts to return
            skip: Number of posts to skip (pagination)
            feed_type: "all" (public + friends), "friends", "own"
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        query = {}

        if feed_type == "own":
            # Only user's own posts
            query["user_id"] = user_id
        elif feed_type == "friends":
            # Posts from friends only (requires friends list)
            # For now, just public posts
            query["visibility"] = {"$in": ["public", "friends-only"]}
        else:
            # All public posts
            query["visibility"] = {"$in": ["public", "friends-only"]}

        posts = list(self.collection.find(query)
                     .sort("created_at", -1)
                     .skip(skip)
                     .limit(limit))

        return posts

    def get_post_by_id(self, post_id):
        """Get a specific post"""
        if isinstance(post_id, str):
            post_id = ObjectId(post_id)
        return self.collection.find_one({"_id": post_id})

    def update_post(self, post_id, update_data):
        """Update post content"""
        if isinstance(post_id, str):
            post_id = ObjectId(post_id)

        update_data["updated_at"] = datetime.utcnow()
        return self.collection.update_one(
            {"_id": post_id},
            {"$set": update_data}
        )

    def delete_post(self, post_id, user_id):
        """Delete a post (only by owner)"""
        if isinstance(post_id, str):
            post_id = ObjectId(post_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        result = self.collection.delete_one({
            "_id": post_id,
            "user_id": user_id
        })
        return result.deleted_count > 0

    def like_post(self, post_id, user_id):
        """Like a post (toggle: if already liked, unlike)"""
        if isinstance(post_id, str):
            post_id = ObjectId(post_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        post = self.get_post_by_id(post_id)
        if not post:
            return None

        likes = post.get("likes", [])

        # Toggle like
        if user_id in likes:
            # Unlike
            result = self.collection.update_one(
                {"_id": post_id},
                {
                    "$pull": {"likes": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return {"liked": False, "like_count": len(likes) - 1}
        else:
            # Like
            result = self.collection.update_one(
                {"_id": post_id},
                {
                    "$addToSet": {"likes": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return {"liked": True, "like_count": len(likes) + 1}

    def add_comment(self, post_id, user_id, comment_text):
        """Add a comment to a post"""
        if isinstance(post_id, str):
            post_id = ObjectId(post_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        comment = {
            "user_id": user_id,
            "text": comment_text,
            "created_at": datetime.utcnow()
        }

        result = self.collection.update_one(
            {"_id": post_id},
            {
                "$push": {"comments": comment},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    def get_user_posts(self, user_id, limit=50, skip=0):
        """Get all posts by a specific user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        posts = list(self.collection.find({"user_id": user_id})
                     .sort("created_at", -1)
                     .skip(skip)
                     .limit(limit))

        return posts
