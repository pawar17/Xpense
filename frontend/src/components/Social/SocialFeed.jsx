import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function SocialFeed({ posts, onNudge, onLike, onComment, onRefresh }) {
  const [expandedPost, setExpandedPost] = useState(null);
  const [commentTexts, setCommentTexts] = useState({});
  const [submittingComment, setSubmittingComment] = useState({});

  const handleLike = async (postId) => {
    if (onLike) {
      await onLike(postId);
      if (onRefresh) onRefresh();
    }
  };

  const handleCommentSubmit = async (postId) => {
    const text = commentTexts[postId]?.trim();
    if (!text || !onComment) return;

    setSubmittingComment(prev => ({ ...prev, [postId]: true }));
    try {
      await onComment(postId, text);
      setCommentTexts(prev => ({ ...prev, [postId]: '' }));
      if (onRefresh) onRefresh();
    } finally {
      setSubmittingComment(prev => ({ ...prev, [postId]: false }));
    }
  };

  const toggleComments = (postId) => {
    setExpandedPost(expandedPost === postId ? null : postId);
  };

  return (
    <div className="space-y-4">
      {posts.map((post, index) => (
        <motion.div
          key={post.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
          className="editorial-card p-4 rounded-3xl space-y-3 bg-white"
        >
          {/* User Header */}
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="text-2xl bg-brand-cream w-10 h-10 flex items-center justify-center rounded-full border border-brand-black/10">
                {post.user?.avatar ?? '👤'}
              </div>
              <div>
                <p className="text-sm font-bold text-gray-800">@{post.user?.username ?? 'user'}</p>
                <p className="text-[10px] text-gray-400 font-mono uppercase">{post.timestamp}</p>
              </div>
            </div>
            <span className="px-2 py-0.5 bg-brand-yellow border border-brand-black rounded-full text-[9px] font-bold uppercase">
              {post.type}
            </span>
          </div>

          {/* Post Content */}
          <p className="text-sm text-gray-700 leading-relaxed font-medium">{post.content}</p>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={() => handleLike(post.id)}
              className={`px-3 py-1.5 border border-brand-black rounded-full text-[9px] font-bold uppercase transition-colors ${
                post.liked
                  ? 'bg-brand-pink text-brand-black'
                  : 'bg-brand-cream text-brand-black hover:bg-brand-pink/50'
              }`}
            >
              {post.liked ? '❤️' : '🤍'} {post.likes}
            </button>
            <button
              type="button"
              onClick={() => toggleComments(post.id)}
              className="px-3 py-1.5 bg-brand-lavender border border-brand-black rounded-full text-[9px] font-bold uppercase hover:bg-brand-lavender/70 transition-colors"
            >
              💬 {post.comments || 0}
            </button>
            <button
              type="button"
              onClick={() => onNudge?.(post.user?.username ?? '')}
              className="px-3 py-1.5 bg-brand-black text-white rounded-full text-[9px] font-bold uppercase hover:bg-brand-black/80 transition-colors"
            >
              🔥 Nudge
            </button>
          </div>

          {/* Comments Section */}
          <AnimatePresence>
            {expandedPost === post.id && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="pt-3 border-t border-brand-black/10 space-y-3">
                  {/* Comment Input */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={commentTexts[post.id] || ''}
                      onChange={(e) => setCommentTexts(prev => ({ ...prev, [post.id]: e.target.value }))}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !submittingComment[post.id]) {
                          handleCommentSubmit(post.id);
                        }
                      }}
                      placeholder="Add a comment..."
                      maxLength={300}
                      className="flex-1 bg-brand-cream border border-brand-black/20 px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-brand-black"
                      disabled={submittingComment[post.id]}
                    />
                    <button
                      type="button"
                      onClick={() => handleCommentSubmit(post.id)}
                      disabled={!commentTexts[post.id]?.trim() || submittingComment[post.id]}
                      className="px-3 py-2 bg-brand-black text-white rounded-xl text-[9px] font-bold uppercase disabled:opacity-50 disabled:cursor-not-allowed hover:bg-brand-black/80 transition-colors"
                    >
                      {submittingComment[post.id] ? '...' : 'Post'}
                    </button>
                  </div>

                  {/* Comments List */}
                  {post.commentsList && post.commentsList.length > 0 ? (
                    <div className="space-y-2">
                      {post.commentsList.map((comment, idx) => (
                        <div key={idx} className="bg-brand-cream/50 border border-brand-black/10 p-2 rounded-xl">
                          <div className="flex items-start gap-2">
                            <div className="text-sm bg-brand-yellow w-6 h-6 flex items-center justify-center rounded-full border border-brand-black/10 shrink-0">
                              {comment.user?.avatar ?? '👤'}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-bold text-gray-800">@{comment.user?.username ?? 'user'}</p>
                              <p className="text-xs text-gray-700 leading-relaxed break-words">{comment.text}</p>
                              <p className="text-[9px] text-gray-400 font-mono uppercase mt-0.5">{comment.timestamp}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 text-center py-2">No comments yet. Be the first!</p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </div>
  );
}
