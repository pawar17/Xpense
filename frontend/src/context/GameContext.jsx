import { createContext, useState, useContext, useEffect, useMemo } from 'react';
import { goalService, questService, userService, gamificationService } from '../services/api';
import { useAuth } from './AuthContext';

const GameContext = createContext();

function toAppGoal(g) {
  if (!g) return null;
  const dailyTarget = Number(g.daily_target ?? g.daily_commitment ?? 0);
  const totalLevels = Number(g.total_levels ?? g.suggested_levels ?? 10);
  const level = Number(g.current_level ?? 0);
  return {
    id: g._id,
    name: g.goal_name,
    category: g.goal_category || 'other',
    targetAmount: Number(g.target_amount),
    currentAmount: Number(g.current_amount),
    level: totalLevels > 0 ? Math.min(level, totalLevels) : 0,
    totalLevels,
    dailyTarget,
    milestones: [],
  };
}

function toAppQuest(q) {
  const d = q.quest_details || q;
  const id = q._id || d._id;
  return {
    id,
    name: d.quest_name || d.name,
    description: d.quest_description || d.description || '',
    category: (d.quest_category || d.category || 'milestone').toLowerCase().replace(/\s/g, '-'),
    pointsReward: d.points_reward ?? 0,
    currencyReward: d.currency_reward ?? 0,
    status: q.status === 'active' ? 'active' : q.status === 'completed' ? 'completed' : 'available',
  };
}

export function GameProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [stats, setStats] = useState({ points: 0, currency: 0, streak: 0, longest_streak: 0 });
  const [goals, setGoals] = useState([]);
  const [activeQuests, setActiveQuests] = useState([]);
  const [availableQuests, setAvailableQuests] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const { data } = await userService.getGameStats();
      setStats(data);
    } catch (_) {}
  };

  const mergeStats = (partial) => {
    if (partial && typeof partial === 'object') {
      setStats((prev) => ({ ...prev, ...partial }));
    }
  };

  const fetchGoals = async () => {
    try {
      const { data } = await goalService.getAll();
      setGoals(data.goals || []);
    } catch (_) {}
  };

  const fetchQuests = async () => {
    try {
      const [activeRes, availableRes] = await Promise.all([
        questService.getActive(),
        questService.getAvailable(),
      ]);
      setActiveQuests(activeRes.data.quests || []);
      setAvailableQuests(availableRes.data.quests || []);
    } catch (_) {}
  };

  const fetchLeaderboard = async () => {
    try {
      const { data } = await gamificationService.getLeaderboard();
      setLeaderboard(data.leaderboard || []);
    } catch (_) {}
  };

  const fetchAll = async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      await Promise.all([fetchStats(), fetchGoals(), fetchQuests(), fetchLeaderboard()]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchAll();
  }, [isAuthenticated]);

  const activeGoal = useMemo(() => goals.find((g) => g.status === 'active') || null, [goals]);
  const appGoal = useMemo(() => toAppGoal(activeGoal), [activeGoal]);
  const appQuests = useMemo(() => {
    const active = (activeQuests || []).map((q) => ({ ...q, status: 'active' }));
    const available = (availableQuests || []).map((q) => ({ ...q, status: 'available' }));
    return [...active.map(toAppQuest), ...available.map(toAppQuest)];
  }, [activeQuests, availableQuests]);

  const createGoal = async (data) => {
    const res = await goalService.create(data);
    await fetchGoals();
    return res.data.goal;
  };

  const contribute = async (goalId, amount) => {
    const res = await goalService.contribute(goalId, amount);
    await fetchGoals();
    await fetchStats();
    return res.data;
  };

  const acceptQuest = async (questId) => {
    await questService.accept(questId);
    await fetchQuests();
  };

  const completeQuest = async (userQuestId) => {
    const res = await questService.complete(userQuestId);
    await fetchQuests();
    await fetchStats();
    return res.data;
  };

  const value = {
    stats,
    goals,
    activeGoal,
    appGoal,
    appQuests,
    leaderboard,
    loading,
    fetchStats,
    fetchGoals,
    fetchQuests,
    fetchAll,
    mergeStats,
    createGoal,
    contribute,
    acceptQuest,
    completeQuest,
  };

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
}

export const useGame = () => {
  const ctx = useContext(GameContext);
  if (!ctx) throw new Error('useGame must be used within GameProvider');
  return ctx;
};
