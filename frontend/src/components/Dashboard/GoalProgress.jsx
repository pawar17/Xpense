import { useState } from 'react';
import { motion } from 'framer-motion';

export default function GoalProgress({ goal, onContribute }) {
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);

  if (!goal) return null;

  const percentage = Math.round((goal.currentAmount / goal.targetAmount) * 100);

  const handleContribute = async (e) => {
    e.preventDefault();
    if (!onContribute || !amount || Number(amount) <= 0) return;
    setLoading(true);
    try {
      await onContribute(goal.id, Number(amount));
      setAmount('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="editorial-card p-6 bg-white space-y-6">
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <p className="text-[10px] font-mono font-bold text-gray-400 uppercase tracking-widest">Active Manifestation</p>
          <h2 className="text-2xl font-heading text-brand-black uppercase tracking-tighter leading-none">{goal.name}</h2>
          <span className="px-2 py-0.5 bg-brand-mint border border-brand-black rounded-full text-[9px] font-bold uppercase">
            Lv. {goal.level} OF {goal.totalLevels}
          </span>
        </div>
        <div className="shrink-0 w-14 h-14 min-w-[3.5rem] min-h-[3.5rem] rounded-full border-2 border-brand-black bg-brand-yellow flex items-center justify-center p-1">
          <span
            className={`font-heading text-brand-black leading-none tabular-nums ${percentage >= 100 ? 'text-lg' : 'text-xl'}`}
          >
            {percentage}%
          </span>
        </div>
      </div>

      <div className="space-y-3">
        <div className="h-10 bg-brand-cream border-2 border-brand-black rounded-full overflow-hidden relative p-1">
          <motion.div
            className="h-full bg-brand-pink border-r-2 border-brand-black rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        <div className="flex justify-between font-mono text-[11px] font-bold uppercase tracking-widest text-brand-black">
          <span>${goal.currentAmount.toLocaleString()} Saved</span>
          <span>Target: ${goal.targetAmount.toLocaleString()}</span>
        </div>
      </div>

      <div className="bg-brand-lavender border-2 border-brand-black p-4 rounded-2xl flex items-center justify-between shadow-[2px_2px_0px_#1A1A1A]">
        <div>
          <p className="text-[10px] font-mono font-bold text-brand-black/60 uppercase tracking-widest">Daily Contribution</p>
          <p className="text-xl font-heading text-brand-black leading-none mt-1">${goal.dailyTarget.toFixed(2)}</p>
        </div>
        <div className="text-2xl">🪙</div>
      </div>

      {onContribute && (
        <form onSubmit={handleContribute} className="flex gap-2">
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Add amount"
            className="flex-1 bg-white border-2 border-brand-black px-4 py-3 rounded-xl font-mono text-sm focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="py-3 px-4 bg-brand-black text-white text-[10px] font-mono font-bold uppercase tracking-widest rounded-xl"
          >
            {loading ? '...' : 'Add'}
          </button>
        </form>
      )}
    </div>
  );
}
