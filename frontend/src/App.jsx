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
import QuestCard from './components/Quests/QuestCard';
import ProfileScreen from './components/Profile/ProfileScreen';
import SocialFeed from './components/Social/SocialFeed';
import VetoRequest from './components/Social/VetoRequest';
import AddVetoRequest from './components/Social/AddVetoRequest';
import AIChat from './components/Chat/AIChat';
import GameWorld from './components/World/GameWorld';
import Confetti from './components/Feedback/Confetti';
import { MOCK_FEED, MOCK_FRIENDS } from './constants';
import { vetoService, gamificationService } from './services/api';
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
    loading: gameLoading,
    createGoal,
    contribute,
    acceptQuest,
    completeQuest,
    fetchAll,
    fetchStats,
  } = useGame();

  const [activeTab, setActiveTab] = useState('home');
  const [history, setHistory] = useState(['home']);
  const [showConfetti, setShowConfetti] = useState(false);
  const [nudgeNotification, setNudgeNotification] = useState(null);
  const [showFriendPicker, setShowFriendPicker] = useState(false);
  const [showAddVeto, setShowAddVeto] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [feed] = useState(MOCK_FEED);
  const [vetoRequests, setVetoRequests] = useState([]);

  const fullUser = useMemo(() => {
    if (!authUser) return null;
    const rank = '#?';
    return {
      id: authUser._id ?? authUser.id,
      name: authUser.name,
      username: authUser.username,
      avatar: authUser.name?.[0]?.toUpperCase() ?? '👤',
      stats: {
        points: stats?.points ?? 0,
        currency: stats?.currency ?? 0,
        streak: stats?.streak ?? 0,
        rank,
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

  useEffect(() => {
    if (authUser) {
      fetchAll();
      fetchVetoRequests();
    }
  }, [authUser]);

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
    if (data?.level_up) {
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

  const handleNudge = (username) => {
    setNudgeNotification(username);
    setTimeout(() => setNudgeNotification(null), 3000);
    setShowFriendPicker(false);
  };

  const handleAddVetoRequest = async ({ item, amount, reason }) => {
    const { data } = await vetoService.create({ item, amount, reason });
    if (data.vetoRequest) {
      setVetoRequests((prev) => [data.vetoRequest, ...prev]);
    }
    toast.success('Sent to Veto Court! Friends can vote.');
  };

  const handleVote = async (requestId, vote) => {
    const userId = fullUser?.id;
    if (!userId) return;
    const request = vetoRequests.find((r) => r.id === requestId);
    if (!request || (request.votes ?? []).some((v) => v.userId === userId)) return;
    try {
      const { data } = await vetoService.vote(requestId, vote);
      setVetoRequests((prev) => prev.filter((r) => r.id !== requestId));
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
            initial={{ y: -100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -100, opacity: 0 }}
            className="fixed top-16 left-0 right-0 z-[100] px-4"
          >
            <div className="editorial-card bg-brand-black text-white p-4 text-center">
              <p className="font-heading text-xs uppercase">Nudge sent to @{nudgeNotification}! ✨</p>
            </div>
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
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {MOCK_FRIENDS.map((friend) => (
                  <button
                    key={friend.id}
                    type="button"
                    onClick={() => handleNudge(friend.username)}
                    className="w-full flex items-center gap-3 p-3 border-2 border-brand-black/10 rounded-2xl hover:bg-brand-yellow"
                  >
                    <span className="text-2xl">{friend.avatar}</span>
                    <p className="font-bold text-sm">@{friend.username}</p>
                  </button>
                ))}
              </div>
              <button type="button" onClick={() => setShowFriendPicker(false)} className="w-full editorial-button py-3 text-xs uppercase">
                Close
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <HUD user={fullUser} goal={appGoal} onAIClick={() => handleTabChange('ai')} onBack={history.length > 1 ? handleBack : undefined} />

      <main className="flex-1 overflow-y-auto px-4 py-6 hide-scrollbar pb-32">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div key="home" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-8">
              <div className="flex gap-4 overflow-x-auto pb-2 hide-scrollbar">
                <StatCard icon="⭐" value={String(fullUser?.stats?.points ?? 0)} label="Experience" color="bg-brand-lavender" />
                <StatCard icon="🔥" value={String(fullUser?.stats?.streak ?? 0)} label="Streak" color="bg-brand-pink" />
                <StatCard icon="🏆" value={fullUser?.stats?.rank ?? '—'} label="Rank" color="bg-brand-mint" />
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
                      <p className="font-mono text-[10px] uppercase font-bold text-gray-400">No active quests. Choose a mission!</p>
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
                onPlaceItem={async () => {
                  try {
                    const { data } = await gamificationService.placePopCityItem();
                    await fetchStats();
                    if (data?.points_earned != null) {
                      toast.success(`Placed! +${data.points_earned} XP, −25 coins`);
                    }
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

          {activeTab === 'social' && (
            <motion.div key="social" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-8">
              <section className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="font-heading text-2xl uppercase tracking-tighter">Veto Court</h2>
                  <button
                    type="button"
                    onClick={() => setShowAddVeto(true)}
                    className="editorial-button py-2 px-4 text-xs uppercase"
                  >
                    Ask for a vote
                  </button>
                </div>
                {vetoRequests.map((v) => (
                  <VetoRequest key={v.id} request={v} onVote={handleVote} currentUserId={fullUser?.id} />
                ))}
              </section>
              <section className="space-y-6">
                <h2 className="font-heading text-2xl uppercase tracking-tighter">Feed</h2>
                <SocialFeed posts={feed} onNudge={() => setShowFriendPicker(true)} />
              </section>
            </motion.div>
          )}

          {activeTab === 'profile' && (
            <motion.div key="profile" variants={pageVariants} initial="initial" animate="animate" exit="exit">
              <ProfileScreen user={fullUser} goal={appGoal} />
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
