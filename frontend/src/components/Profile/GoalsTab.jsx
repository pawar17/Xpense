import { useState, useEffect } from 'react';
import { goalService } from '../../services/api';
import toast from 'react-hot-toast';

export default function GoalsTab({ goals: initialGoals, onGoalsChange }) {
  const [goals, setGoals] = useState(initialGoals || []);
  const [editingId, setEditingId] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [archivedGoals, setArchivedGoals] = useState([]);
  const [archivedLoading, setArchivedLoading] = useState(false);
  const [form, setForm] = useState({ goal_name: '', goal_category: 'other', target_amount: '', target_date: '' });

  useEffect(() => {
    setGoals(initialGoals || []);
  }, [initialGoals]);

  const refreshGoals = async () => {
    try {
      const { data } = await goalService.getAll();
      setGoals(data.goals || []);
      onGoalsChange?.(data.goals);
    } catch (_) {}
  };

  const handleUpdate = async (goalId, updates) => {
    try {
      await goalService.update(goalId, updates);
      toast.success('Goal updated');
      setEditingId(null);
      refreshGoals();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Update failed');
    }
  };

  const handleReorder = async (goalIds) => {
    try {
      const { data } = await goalService.reorder(goalIds);
      setGoals(data.goals || []);
      onGoalsChange?.(data.goals);
      toast.success('Order saved');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Reorder failed');
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!form.goal_name.trim() || !form.target_amount) {
      toast.error('Name and target amount required');
      return;
    }
    try {
      await goalService.create({
        goal_name: form.goal_name.trim(),
        goal_category: form.goal_category || 'other',
        target_amount: parseFloat(form.target_amount),
        target_date: form.target_date || null
      });
      toast.success('Goal created');
      setShowAdd(false);
      setForm({ goal_name: '', goal_category: 'other', target_amount: '', target_date: '' });
      refreshGoals();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Create failed');
    }
  };

  const moveGoal = (index, direction) => {
    const next = [...goals];
    const ni = index + direction;
    if (ni < 0 || ni >= next.length) return;
    [next[index], next[ni]] = [next[ni], next[index]];
    handleReorder(next.map((g) => g._id));
  };

  const fetchArchived = async () => {
    setArchivedLoading(true);
    try {
      const { data } = await goalService.getArchived();
      setArchivedGoals(data.goals || []);
      setShowArchived(true);
    } catch (_) {
      setArchivedGoals([]);
    } finally {
      setArchivedLoading(false);
    }
  };

  const handleArchive = async (goalId) => {
    try {
      await goalService.archive(goalId);
      toast.success('Goal archived');
      refreshGoals();
      if (showArchived) fetchArchived();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Archive failed');
    }
  };

  const handleDeleteArchived = async (goalId) => {
    if (!window.confirm('Permanently delete this goal from archive?')) return;
    try {
      await goalService.deleteGoal(goalId);
      toast.success('Goal deleted');
      setArchivedGoals((prev) => prev.filter((g) => g._id !== goalId));
    } catch (err) {
      toast.error(err.response?.data?.error || 'Delete failed');
    }
  };

  const categories = ['other', 'house', 'vacation', 'debt', 'shopping', 'emergency'];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b-2 border-brand-black pb-2">
        <h3 className="font-heading text-xl uppercase tracking-tighter">My Goals</h3>
        <button
          type="button"
          onClick={() => setShowAdd(!showAdd)}
          className="editorial-button py-2 px-4 text-xs uppercase"
        >
          {showAdd ? 'Cancel' : 'Add goal'}
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="editorial-card p-6 space-y-4">
          <input
            type="text"
            value={form.goal_name}
            onChange={(e) => setForm((f) => ({ ...f, goal_name: e.target.value }))}
            placeholder="Goal name"
            className="w-full border-2 border-brand-black p-3 rounded-xl font-mono text-sm"
          />
          <select
            value={form.goal_category}
            onChange={(e) => setForm((f) => ({ ...f, goal_category: e.target.value }))}
            className="w-full border-2 border-brand-black p-3 rounded-xl font-mono text-sm"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.target_amount}
            onChange={(e) => setForm((f) => ({ ...f, target_amount: e.target.value }))}
            placeholder="Target amount ($)"
            className="w-full border-2 border-brand-black p-3 rounded-xl font-mono text-sm"
          />
          <input
            type="date"
            value={form.target_date}
            onChange={(e) => setForm((f) => ({ ...f, target_date: e.target.value }))}
            className="w-full border-2 border-brand-black p-3 rounded-xl font-mono text-sm"
          />
          <button type="submit" className="w-full editorial-button py-3 uppercase text-sm">
            Create goal
          </button>
        </form>
      )}

      <ul className="space-y-4">
        {goals.map((goal, index) => (
          <li key={goal._id} className="editorial-card p-4">
            {editingId === goal._id ? (
              <GoalEditForm
                goal={goal}
                onSave={(updates) => handleUpdate(goal._id, updates)}
                onCancel={() => setEditingId(null)}
                categories={categories}
              />
            ) : (
              <>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold">{goal.goal_name}</p>
                    <p className="text-xs text-gray-500 uppercase">{goal.goal_category}</p>
                    <p className="text-sm">
                      ${Number(goal.current_amount || 0).toLocaleString()} / ${Number(goal.target_amount || 0).toLocaleString()}
                    </p>
                    {goal.target_date && (
                      <p className="text-[10px] text-gray-500">By {new Date(goal.target_date).toLocaleDateString()}</p>
                    )}
                    {goal.daily_commitment != null && goal.daily_commitment > 0 && (
                      <p className="text-xs font-mono mt-1 text-brand-lavender">
                        Save <strong>${Number(goal.daily_commitment).toFixed(2)}</strong>/day
                        {goal.days_to_goal != null && goal.days_to_goal > 0 && ` · ${goal.days_to_goal} days to goal`}
                      </p>
                    )}
                    {goal.suggested_levels != null && goal.amount_per_level != null && goal.amount_per_level > 0 && (
                      <p className="text-[10px] text-gray-500 mt-0.5">
                        Levels 1–{goal.suggested_levels} · Each level = ${Number(goal.amount_per_level).toFixed(0)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => moveGoal(index, -1)}
                      disabled={index === 0}
                      className="p-1 text-lg disabled:opacity-30"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => moveGoal(index, 1)}
                      disabled={index === goals.length - 1}
                      className="p-1 text-lg disabled:opacity-30"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(goal._id)}
                      className="text-[10px] font-mono uppercase text-gray-600"
                    >
                      Edit
                    </button>
                    {(goal.status === 'completed' || goal.status === 'pending') && (
                      <button
                        type="button"
                        onClick={() => handleArchive(goal._id)}
                        className="text-[10px] font-mono uppercase text-brand-pink"
                      >
                        Archive
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-[9px] text-gray-400 mt-1">
                  Queue order: {index + 1}
                  {goal.status && goal.status !== 'active' && goal.status !== 'queued' && (
                    <span className="ml-2 px-1.5 py-0.5 rounded bg-brand-cream uppercase font-bold">{goal.status}</span>
                  )}
                </p>
              </>
            )}
          </li>
        ))}
      </ul>

      <section className="border-t-2 border-brand-black pt-6">
        <div className="flex justify-between items-center pb-2">
          <h3 className="font-heading text-lg uppercase tracking-tighter">Archived goals</h3>
          <button
            type="button"
            onClick={() => (showArchived ? setShowArchived(false) : fetchArchived())}
            className="text-[10px] font-mono uppercase text-gray-600 hover:text-brand-black"
          >
            {archivedLoading ? 'Loading…' : showArchived ? 'Hide archived' : 'View archived'}
          </button>
        </div>
        {showArchived && (
          <ul className="space-y-3">
            {archivedGoals.length === 0 ? (
              <li className="text-sm text-gray-500 font-mono">No archived goals. Achieved goals move here automatically.</li>
            ) : (
              archivedGoals.map((goal) => (
                <li key={goal._id} className="editorial-card p-4 bg-brand-cream/50 flex justify-between items-start gap-2">
                  <div>
                    <p className="font-bold">{goal.goal_name}</p>
                    <p className="text-xs text-gray-500">
                      ${Number(goal.current_amount || 0).toLocaleString()} / ${Number(goal.target_amount || 0).toLocaleString()}
                      {goal.completed_at && (
                        <span className="ml-2">Completed {new Date(goal.completed_at).toLocaleDateString()}</span>
                      )}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteArchived(goal._id)}
                    className="text-[10px] font-mono uppercase text-red-600 hover:text-red-700"
                  >
                    Delete
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </section>
    </div>
  );
}

function GoalEditForm({ goal, onSave, onCancel, categories }) {
  const [name, setName] = useState(goal.goal_name || '');
  const [category, setCategory] = useState(goal.goal_category || 'other');
  const [target, setTarget] = useState(String(goal.target_amount || ''));
  const [date, setDate] = useState(goal.target_date ? goal.target_date.slice(0, 10) : '');

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full border-2 border-brand-black p-2 rounded-lg text-sm"
      />
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        className="w-full border-2 border-brand-black p-2 rounded-lg text-sm"
      >
        {categories.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
      <input
        type="number"
        min="0"
        value={target}
        onChange={(e) => setTarget(e.target.value)}
        className="w-full border-2 border-brand-black p-2 rounded-lg text-sm"
      />
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        className="w-full border-2 border-brand-black p-2 rounded-lg text-sm"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onSave({ goal_name: name, goal_category: category, target_amount: parseFloat(target) || 0, target_date: date || null })}
          className="flex-1 editorial-button py-2 text-xs uppercase"
        >
          Save
        </button>
        <button type="button" onClick={onCancel} className="flex-1 py-2 border-2 border-brand-black rounded-xl text-xs uppercase">
          Cancel
        </button>
      </div>
    </div>
  );
}
