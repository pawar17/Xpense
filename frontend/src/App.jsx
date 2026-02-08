import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './context/AuthContext';
import { useGame } from './context/GameContext';
import AuthScreen from './components/Auth/AuthScreen';
import Onboarding from './components/Onboarding/Onboarding';
import HUD from './components/Layout/HUD';
import BottomNav from './components/Layout/BottomNav';
import StatCard from './components/Dashboard/StatCard';
import GoalProgress from './components/Dashboard/GoalProgress';
import Leaderboard from './components/Dashboard/Leaderboard';
import StreakCalendar from './components/Dashboard/StreakCalendar';
import QuestCard from './components/Quests/QuestCard';
import ProfileScreen from './components/Profile/ProfileScreen';
import SocialFeed from './components/Social/SocialFeed';
import VetoRequest from './components/Social/VetoRequest';
import AddVetoRequest from './components/Social/AddVetoRequest';
import AIChat from './components/Chat/AIChat';
import GameWorld from './components/World/GameWorld';
import Confetti from './components/Feedback/Confetti';
import { MOCK_FRIENDS } from './constants';
import { vetoService, gamificationService, friendsService, nudgeService, questService, feedService } from './services/api';
import toast from 'react-hot-toast';

const pageVariants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { opacity: 0, x: -20, transition: { duration: 0.2 } },
};

export default function App() {
  const { user: authUser, loading: authLoading } = useAuth();
  const {
    goals,
    stats,
    appGoal,
    appQuests,
    leaderboard,
    loading: gameLoading,
    createGoal,
    contribute,
    acceptQuest,
    completeQuest,
    fetchAll,
    fetchStats,
    fetchGoals,
    fetchQuests,
    mergeStats,
  } = useGame();

  const [activeTab, setActiveTab] = useState('home');
  const [history, setHistory] = useState(['home']);
  const [showConfetti, setShowConfetti] = useState(false);
  const [nudgeNotification, setNudgeNotification] = useState(null);
  const [showFriendPicker, setShowFriendPicker] = useState(false);
  const [showAddVeto, setShowAddVeto] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [feed, setFeed] = useState([]);
  const [feedLoading, setFeedLoading] = useState(false);
  const [postContent, setPostContent] = useState('');
  const [postSubmitting, setPostSubmitting] = useState(false);
  const [vetoRequests, setVetoRequests] = useState([]);
  const [friends, setFriends] = useState([]);
  const [nudgedUserIds, setNudgedUserIds] = useState([]);
  const [nudgesReceived, setNudgesReceived] = useState([]);
  const [dismissedNudgeId, setDismissedNudgeId] = useState(null);
  const [generatedQuests, setGeneratedQuests] = useState([]);
  const [generatedQuestsBasedOn, setGeneratedQuestsBasedOn] = useState(null);
  const [leaderboardMode, setLeaderboardMode] = useState('all');
  const [friendsLeaderboard, setFriendsLeaderboard] = useState([]);

  const fullUser = useMemo(() => {
    if (!authUser) return null;
    const rank = stats?.rank != null ? stats.rank : null;
    return {
      id: authUser._id ?? authUser.id,
      name: authUser.name,
      username: authUser.username,
      avatar: authUser.name?.[0]?.toUpperCase() ?? '👤',
      stats: {
        points: stats?.points ?? 0,
        currency: stats?.currency ?? 0,
        streak: stats?.streak ?? 0,
        rank: rank != null ? `#${rank}` : '—',
        vetoTokens: stats?.veto_tokens ?? 0,
        vetoEarned: stats?.veto_earned ?? 0,
        vetoUsed: stats?.veto_used ?? 0,
        popCityPlacementCount: stats?.pop_city_placement_count ?? 0,
        approveTokens: stats?.approve_tokens ?? 0,
        approveEarned: stats?.approve_earned ?? 0,
        approveUsed: stats?.approve_used ?? 0,
      },
    };
  }, [authUser, stats]);

  const hasGoals = (goals?.length ?? 0) > 0;
  const hasActiveGoal = appGoal != null;

  const fetchVetoRequests = async () => {
    try {
      const { data } = await vetoService.getAll();
      setVetoRequests(data.vetoRequests || []);
    } catch (_) {
      setVetoRequests([]);
    }
  };

  const fetchFriendsLeaderboard = async () => {
    try {
      const { data } = await gamificationService.getFriendsLeaderboard(50);
      setFriendsLeaderboard(data.leaderboard || []);
    } catch (_) {
      setFriendsLeaderboard([]);
    }
  };

  const fetchFriends = async () => {
    try {
      const { data } = await friendsService.getList();
      setFriends(data.friends || []);
    } catch (_) {
      setFriends([]);
    }
  };

  const fetchNudges = async () => {
    try {
      const { data } = await nudgeService.getMyNudges();
      setNudgesReceived(data.nudges || []);
    } catch (_) {
      setNudgesReceived([]);
    }
  };

  useEffect(() => {
    if (leaderboardMode === 'friends') fetchFriendsLeaderboard();
  }, [leaderboardMode]);

  useEffect(() => {
    if (authUser) {
      fetchAll();
      fetchVetoRequests();
      fetchFriendsLeaderboard();
      fetchNudges();
    }
  }, [authUser]);

  useEffect(() => {
    if (showFriendPicker) {
      fetchFriends();
      nudgeService.getSentToUserIds().then(({ data }) => setNudgedUserIds(data.sentToUserIds || [])).catch(() => setNudgedUserIds([]));
    }
  }, [showFriendPicker]);

  useEffect(() => {
    if (activeTab === 'quests') {
      questService.getGenerated()
        .then(({ data }) => {
          setGeneratedQuests(data.quests || []);
          setGeneratedQuestsBasedOn(data.basedOn || null);
        })
        .catch(() => {
          setGeneratedQuests([]);
          setGeneratedQuestsBasedOn(null);
        });
    }
  }, [activeTab]);

  const fetchFeed = async () => {
    setFeedLoading(true);
    try {
      const { data } = await feedService.getFeed({ type: 'all', limit: 50 });
      setFeed(data.posts || []);
    } catch (_) {
      setFeed([]);
    } finally {
      setFeedLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'social') {
      fetchStats();
      fetchVetoRequests();
      fetchFeed();
    }
  }, [activeTab]);

  const triggerConfetti = () => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3000);
  };

  const handleTabChange = (tab) => {
    if (tab === activeTab) return;
    setHistory((prev) => [...prev, tab]);
    setActiveTab(tab);
  };

  const handleBack = () => {
    if (history.length > 1) {
      const next = [...history];
      next.pop();
      setHistory(next);
      setActiveTab(next[next.length - 1]);
    }
  };

  const handleContribute = async (goalId, amount) => {
    const data = await contribute(goalId, amount);
    if (data?.goal_completed) {
      toast.success(data.message || '🎉 Goal achieved!');
      triggerConfetti();
    } else if (data?.level_up) {
      toast.success(`Level up! +${data.rewards?.points ?? 0} XP, +${data.rewards?.currency ?? 0} coins`);
      triggerConfetti();
    } else {
      toast.success('Contribution added!');
    }
  };

  const handleAcceptQuest = async (questId) => {
    await acceptQuest(questId);
    toast.success('Quest accepted!');
    triggerConfetti();
  };

  const handleCompleteQuest = async (questId) => {
    const data = await completeQuest(questId);
    toast.success(`+${data?.rewards?.points ?? 0} XP, +${data?.rewards?.currency ?? 0} coins!`);
    triggerConfetti();
  };

  const handleNudge = async (friend) => {
    try {
      await nudgeService.send({
        toUserId: friend.id,
        goalId: appGoal?.id ?? goals?.[0]?._id,
        goalName: appGoal?.name ?? goals?.[0]?.goal_name ?? 'your goal',
      });
      setNudgedUserIds((prev) => (prev.includes(friend.id) ? prev : [...prev, friend.id]));
      setNudgeNotification(friend.name || friend.username);
      setTimeout(() => setNudgeNotification(null), 3000);
      setShowFriendPicker(false);
      toast.success(`Sent nudge to ${friend.name || friend.username}!`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not send nudge');
    }
  };

  const handleDismissNudge = async (nudgeId) => {
    setDismissedNudgeId(nudgeId);
    try {
      await nudgeService.markRead(nudgeId);
    } catch (_) {}
  };

  const handleAddVetoRequest = async ({ item, amount, reason }) => {
    try {
      const { data } = await vetoService.create({ item, amount, reason });
      if (data.vetoRequest) {
        setVetoRequests((prev) => [data.vetoRequest, ...prev]);
        fetchStats();
        setShowAddVeto(false);
        toast.success('Sent to Veto Court! Friends can vote.');
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not send to Veto Court');
    }
  };

  const handleVote = async (requestId, vote) => {
    const userId = fullUser?.id;
    if (!userId) return;
    const request = vetoRequests.find((r) => r.id === requestId);
    if (!request || (request.votes ?? []).some((v) => v.userId === userId)) return;
    try {
      const { data } = await vetoService.vote(requestId, vote);
      setVetoRequests((prev) => prev.filter((r) => r.id !== requestId));
      fetchStats();
      if (data.rejected || vote === 'veto') {
        toast.success('Rejected. Removed from your feed.');
      } else {
        toast.success('Approved. Removed from your feed.');
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Vote failed');
    }
  };

  if (authLoading || (authUser && gameLoading && !appGoal)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-cream">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-black" />
      </div>
    );
  }

  if (!authUser) {
    return <AuthScreen onLoginSuccess={() => fetchAll()} />;
  }

  if (!hasGoals && !showOnboarding) {
    return <Onboarding onComplete={() => fetchAll()} />;
  }
  if (showOnboarding) {
    return (
      <Onboarding
        onComplete={() => {
          setShowOnboarding(false);
          fetchAll();
        }}
      />
    );
  }

  const activeQuests = appQuests.filter((q) => q.status === 'active');
  const availableQuests = appQuests.filter((q) => q.status === 'available');

  return (
    <div className="min-h-screen flex flex-col bg-brand-cream relative overflow-hidden">
      <AnimatePresence>{showConfetti && <Confetti />}</AnimatePresence>

      <AnimatePresence>
        {nudgeNotification && (
          <motion.div
            key="nudge-sent"
            initial={{ y: -100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -100, opacity: 0 }}
            transition={{ type: 'tween', duration: 0.25 }}
            className="fixed top-16 left-0 right-0 z-[100] px-4"
          >
            <div className="editorial-card bg-brand-black text-white p-4 text-center shadow-lg">
              <p className="font-heading text-xs uppercase">Sent nudge to {nudgeNotification}! ✨</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {nudgesReceived.find((n) => !n.readAt && n.id !== dismissedNudgeId) && (
          <motion.div
            initial={{ y: -80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -80, opacity: 0 }}
            className="fixed top-16 left-0 right-0 z-[90] px-4"
          >
            {(() => {
              const nudge = nudgesReceived.find((n) => !n.readAt && n.id !== dismissedNudgeId);
              if (!nudge) return null;
              return (
                <div className="editorial-card bg-brand-pink/90 text-brand-black p-4 flex items-center justify-between gap-2">
                  <p className="font-heading text-xs uppercase flex-1">
                    <strong>{nudge.fromName}</strong> nudged you to keep pushing for your goals! ✨
                  </p>
                  <button
                    type="button"
                    onClick={() => handleDismissNudge(nudge.id)}
                    className="text-[10px] font-mono uppercase font-bold"
                  >
                    Dismiss
                  </button>
                </div>
              );
            })()}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showAddVeto && (
          <AddVetoRequest
            user={fullUser}
            onAdd={handleAddVetoRequest}
            onClose={() => setShowAddVeto(false)}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {showFriendPicker && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-brand-black/40 z-[200] flex items-center justify-center p-4"
            onClick={() => setShowFriendPicker(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              className="editorial-card bg-white w-full max-w-sm p-6 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="font-heading text-xl uppercase text-center">Nudge a Friend</h3>
              <p className="text-[10px] text-center text-gray-500">Pick a friend to nudge. You can only nudge each friend once.</p>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {friends.length === 0 ? (
                  <p className="text-xs text-gray-500 text-center py-4">Add friends from Profile to nudge them.</p>
                ) : (
                  friends.map((friend) => {
                    const alreadyNudged = nudgedUserIds.includes(friend.id);
                    return (
                      <button
                        key={friend.id}
                        type="button"
                        onClick={() => !alreadyNudged && handleNudge(friend)}
                        disabled={alreadyNudged}
                        className={`w-full flex items-center gap-3 p-3 border-2 rounded-2xl text-left ${
                          alreadyNudged ? 'border-brand-black/10 bg-gray-100 opacity-60 cursor-not-allowed' : 'border-brand-black/10 hover:bg-brand-yellow'
                        }`}
                      >
                        <span className="w-10 h-10 bg-brand-lavender rounded-full flex items-center justify-center font-bold text-sm shrink-0">
                          {(friend.name || friend.username || '?')[0].toUpperCase()}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm">{friend.name || friend.username}</p>
                          <p className="text-[10px] text-gray-500">@{friend.username}</p>
                          {alreadyNudged && <p className="text-[9px] font-mono uppercase text-gray-500 mt-0.5">Already nudged</p>}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
              <button type="button" onClick={() => setShowFriendPicker(false)} className="w-full editorial-button py-3 text-xs uppercase">
                Close
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <HUD user={fullUser} goal={appGoal} onAIClick={() => handleTabChange('ai')} onBack={history.length > 1 ? handleBack : undefined} />

      <main className="flex-1 flex flex-col min-h-0 overflow-y-auto px-4 py-6 hide-scrollbar pb-32">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div key="home" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-8">
              <div className="flex gap-4 overflow-x-auto pb-2 hide-scrollbar">
                <StatCard icon="⭐" value={String(fullUser?.stats?.points ?? 0)} label="Experience" color="bg-brand-lavender" />
                <StatCard icon="🔥" value={String(fullUser?.stats?.streak ?? 0)} label="Streak" color="bg-brand-pink" onClick={() => handleTabChange('calendar')} />
                <StatCard icon="🏆" value={fullUser?.stats?.rank ?? '—'} label="Rank" color="bg-brand-mint" onClick={() => handleTabChange('leaderboard')} />
              </div>
              {appGoal ? (
                <GoalProgress goal={appGoal} onContribute={handleContribute} />
              ) : (
                <div className="editorial-card p-6 text-center">
                  <p className="font-mono text-[10px] uppercase text-gray-500 mb-2">No active goal</p>
                  <button type="button" onClick={() => setShowOnboarding(true)} className="w-full editorial-button py-3 text-sm uppercase">
                    Create new goal
                  </button>
                </div>
              )}
              <section className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-heading text-xl uppercase tracking-tighter">Daily Missions</h3>
                  <button type="button" onClick={() => handleTabChange('quests')} className="text-[10px] font-mono underline uppercase font-bold">
                    See All →
                  </button>
                </div>
                <div className="space-y-4">
                  {activeQuests.map((quest) => (
                    <QuestCard key={quest.id} quest={quest} onComplete={handleCompleteQuest} />
                  ))}
                  {activeQuests.length === 0 && (
                    <button
                      type="button"
                      onClick={() => handleTabChange('quests')}
                      className="w-full editorial-card p-6 border-dashed border-2 border-brand-black/20 opacity-60 text-center bg-white"
                    >
                      <p className="font-mono text-[10px] uppercase font-bold text-gray-400">No other active quests. Choose a mission!</p>
                    </button>
                  )}
                </div>
              </section>
            </motion.div>
          )}

          {activeTab === 'play' && (
            <motion.div key="play" variants={pageVariants} initial="initial" animate="animate" exit="exit">
              <GameWorld
                goalType={appGoal?.category ?? 'other'}
                progressPercent={appGoal ? (appGoal.currentAmount / appGoal.targetAmount) * 100 : 0}
                currency={fullUser?.stats?.currency ?? 0}
                initialPlacements={stats?.pop_city_placements}
                onPlaceItem={async (index, item) => {
                  try {
                    const { data } = await gamificationService.placePopCityItem({ index, item });
                    if (data?.stats) mergeStats(data.stats);
                    await fetchStats();
                    if (data?.points_earned != null) {
                      toast.success(`Placed! +${data.points_earned} XP, −25 coins`);
                    }
                    return data?.placements;
                  } catch (err) {
                    const msg = err.response?.data?.error || 'Could not place item';
                    toast.error(msg);
                    throw err;
                  }
                }}
              />
            </motion.div>
          )}

          {activeTab === 'quests' && (
            <motion.div key="quests" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-10">
              <div className="space-y-2">
                <h2 className="font-heading text-2xl uppercase tracking-tighter">Quest Center</h2>
                <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold">Track and take on challenges</p>
              </div>
              <section className="space-y-4">
                <h3 className="font-heading text-sm uppercase tracking-widest border-b-2 border-brand-black pb-1">Current Tracker</h3>
                {activeQuests.length > 0 ? (
                  activeQuests.map((quest) => <QuestCard key={quest.id} quest={quest} onComplete={handleCompleteQuest} />)
                ) : (
                  <div className="p-8 text-center bg-white border-2 border-dashed border-gray-200 rounded-[2rem]">
                    <p className="text-2xl mb-2">🔭</p>
                    <p className="font-mono text-[9px] uppercase font-bold text-gray-400">Your tracker is empty. Enroll below!</p>
                  </div>
                )}
              </section>
              {generatedQuests.length > 0 && (() => {
                const addedOrCompletedNames = new Set((appQuests || []).map((aq) => aq.name));
                const stillSuggested = generatedQuests.filter((q) => !addedOrCompletedNames.has(q.name));
                if (stillSuggested.length === 0) return null;
                return (
                <section className="space-y-4">
                  <h3 className="font-heading text-sm uppercase tracking-widest border-b-2 border-brand-black pb-1">Suggested for you (from your spending)</h3>
                  <p className="text-[10px] text-gray-500">
                    {generatedQuestsBasedOn?.summary ?? 'Personalized quest ideas based on your spending. Upload statements in Profile → Bank Statements to improve suggestions.'}
                  </p>
                  <div className="space-y-3">
                    {stillSuggested.map((q, i) => (
                      <div key={i} className="editorial-card p-4 flex flex-col sm:flex-row sm:items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm">{q.name}</p>
                          <p className="text-xs text-gray-600">{q.description}</p>
                          <p className="text-[10px] text-gray-500 mt-1">+{q.points_reward ?? 0} XP · +{q.currency_reward ?? 0} coins when done</p>
                        </div>
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await questService.addFromSuggestion({
                                name: q.name,
                                description: q.description || '',
                                category: q.category || 'milestone',
                                points_reward: q.points_reward ?? 25,
                                currency_reward: q.currency_reward ?? 10,
                              });
                              toast.success('Added to your tracker! Mark it done when you complete it.');
                              fetchQuests();
                            } catch (err) {
                              toast.error(err.response?.data?.error || 'Could not add quest');
                            }
                          }}
                          className="shrink-0 py-2 px-4 border-2 border-brand-black text-[10px] font-mono font-bold uppercase rounded-xl hover:bg-brand-yellow"
                        >
                          Add to my quests
                        </button>
                      </div>
                    ))}
                  </div>
                </section>
                );
              })()}
              <section className="space-y-4">
                <h3 className="font-heading text-sm uppercase tracking-widest border-b-2 border-brand-black pb-1">Available Missions</h3>
                <div className="space-y-6">
                  {availableQuests.map((quest) => (
                    <QuestCard key={quest.id} quest={quest} onAccept={handleAcceptQuest} />
                  ))}
                </div>
              </section>
            </motion.div>
          )}

          {activeTab === 'calendar' && (
            <motion.div key="calendar" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="flex flex-col flex-1 min-h-0 w-full">
              <div className="space-y-2 shrink-0">
                <h2 className="font-heading text-2xl uppercase tracking-tighter">Streak Calendar</h2>
                <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold">Days you achieved this month</p>
              </div>
              <StreakCalendar />
            </motion.div>
          )}

          {activeTab === 'leaderboard' && (
            <motion.div key="leaderboard" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-8">
              <div className="space-y-2">
                <h2 className="font-heading text-2xl uppercase tracking-tighter">Leaderboard</h2>
                <p className="font-mono text-[10px] text-gray-500 uppercase tracking-widest font-bold">Ranked by XP</p>
              </div>
              <div className="flex gap-2 p-1 bg-white rounded-full border-2 border-brand-black w-fit">
                <button
                  type="button"
                  onClick={() => setLeaderboardMode('all')}
                  className={`px-4 py-2 rounded-full text-xs font-mono font-bold uppercase transition-colors ${leaderboardMode === 'all' ? 'bg-brand-pink text-brand-black' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setLeaderboardMode('friends')}
                  className={`px-4 py-2 rounded-full text-xs font-mono font-bold uppercase transition-colors ${leaderboardMode === 'friends' ? 'bg-brand-pink text-brand-black' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  Friends
                </button>
              </div>
              <Leaderboard
                leaderboard={leaderboardMode === 'friends' ? friendsLeaderboard : leaderboard}
                currentUserId={fullUser?.id}
                limit={leaderboardMode === 'friends' ? 50 : 20}
                emptyMessage={leaderboardMode === 'friends' ? 'Add friends to see rankings by XP.' : 'No rankings yet. Earn XP to climb!'}
              />
            </motion.div>
          )}

          {activeTab === 'social' && (
            <motion.div key="social" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-8">
              <section className="space-y-6">
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <h2 className="font-heading text-2xl uppercase tracking-tighter">Veto Court</h2>
                  <button
                    type="button"
                    onClick={() => setShowAddVeto(true)}
                    className="editorial-button py-2 px-4 text-xs uppercase"
                  >
                    Ask for a vote
                  </button>
                </div>
                <p className="text-xs text-gray-500 font-mono">
                  Say Go for it: fill one full row in Pop City (Play tab) to vote on 1 request; two full rows = 2 votes. You have {(fullUser?.stats?.approveTokens ?? 0)} vote{(fullUser?.stats?.approveTokens ?? 0) !== 1 ? 's' : ''} left.
                </p>
                {vetoRequests.map((v) => (
                  <VetoRequest key={v.id} request={v} onVote={handleVote} currentUserId={fullUser?.id} approveTokens={fullUser?.stats?.approveTokens ?? 0} />
                ))}
              </section>
              <section className="space-y-4">
                <h3 className="font-heading text-sm uppercase tracking-widest border-b-2 border-brand-black pb-1">Nudge a friend</h3>
                <p className="text-[10px] text-gray-500 font-mono">Send a friend a nudge to keep pushing for their goals. You can only nudge each friend once.</p>
                <button
                  type="button"
                  onClick={() => setShowFriendPicker(true)}
                  className="w-full editorial-card p-4 flex items-center gap-4 border-2 border-brand-yellow bg-brand-yellow/30"
                >
                  <span className="text-3xl">👋</span>
                  <div className="text-left flex-1">
                    <p className="font-bold text-sm uppercase">Pick a friend to nudge</p>
                    <p className="text-[10px] text-gray-600">One nudge per friend</p>
                  </div>
                  <span className="text-brand-black">→</span>
                </button>
              </section>
              <section className="space-y-6">
                <h2 className="font-heading text-2xl uppercase tracking-tighter">Feed</h2>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const content = postContent?.trim();
                    if (!content || postSubmitting) return;
                    setPostSubmitting(true);
                    try {
                      await feedService.createPost({ content });
                      setPostContent('');
                      await fetchFeed();
                      toast.success('Post shared!');
                    } catch (err) {
                      toast.error(err.response?.data?.error || 'Failed to post');
                    } finally {
                      setPostSubmitting(false);
                    }
                  }}
                  className="editorial-card p-4 flex gap-2 bg-white"
                >
                  <input
                    type="text"
                    value={postContent}
                    onChange={(e) => setPostContent(e.target.value)}
                    placeholder="Share an update..."
                    maxLength={500}
                    className="flex-1 border-2 border-brand-black px-4 py-3 rounded-xl font-mono text-sm focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!postContent?.trim() || postSubmitting}
                    className="py-3 px-4 bg-brand-black text-white text-[10px] font-mono font-bold uppercase tracking-widest rounded-xl disabled:opacity-50"
                  >
                    {postSubmitting ? '...' : 'Post'}
                  </button>
                </form>
                <SocialFeed
                  posts={feed}
                  loading={feedLoading}
                  onNudge={() => setShowFriendPicker(true)}
                  onLike={async (postId) => {
                    try {
                      await feedService.likePost(postId);
                      fetchFeed();
                    } catch (e) {
                      toast.error(e.response?.data?.error || 'Could not like post');
                    }
                  }}
                  onComment={async (postId, text) => {
                    try {
                      await feedService.addComment(postId, text);
                      fetchFeed();
                    } catch (e) {
                      toast.error(e.response?.data?.error || 'Could not post comment');
                    }
                  }}
                  onRefresh={fetchFeed}
                />
              </section>
            </motion.div>
          )}

          {activeTab === 'profile' && (
            <motion.div key="profile" variants={pageVariants} initial="initial" animate="animate" exit="exit">
              <ProfileScreen user={fullUser} goal={appGoal} refetchGoals={fetchGoals} />
            </motion.div>
          )}

          {activeTab === 'ai' && (
            <motion.div key="ai" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-[65vh]">
              <AIChat user={fullUser} goal={appGoal} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <BottomNav active={activeTab} setActive={handleTabChange} />
    </div>
  );
}
