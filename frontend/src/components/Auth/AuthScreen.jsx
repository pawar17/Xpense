import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import toast from 'react-hot-toast';
import RegisterScreen from './RegisterScreen';

export default function AuthScreen({ onLoginSuccess }) {
  const { login } = useAuth();
  const [showRegister, setShowRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      toast.error('Enter username and password');
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password);
      onLoginSuccess?.();
    } catch (err) {
      const res = err?.response;
      console.error('Login error:', res?.status, res?.data || err.message);
      const backendMsg = res?.data?.error;
      const msg =
        backendMsg ||
        (err.code === 'ERR_NETWORK'
          ? 'Cannot reach server. Is the backend running on port 5001?'
          : res?.status === 401
            ? 'Invalid username or password'
            : `Login failed${res?.status ? ` (${res.status})` : ''}`);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (showRegister) {
    return (
      <RegisterScreen
        onSuccess={onLoginSuccess}
        onBackToLogin={() => setShowRegister(false)}
      />
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-brand-cream">
      <div className="mb-10 text-center space-y-4">
        <div className="text-6xl mb-4">✨</div>
        <h1 className="font-heading text-5xl md:text-6xl tracking-tighter uppercase leading-none text-brand-black">
          XPense
        </h1>
        <p className="font-mono text-[11px] text-gray-500 uppercase tracking-[0.3em]">
          The Editorial Savings Game
        </p>
      </div>

      <div className="w-full max-w-sm space-y-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="USERNAME"
            className="w-full bg-white border-2 border-brand-black p-4 rounded-full text-sm font-bold focus:outline-none placeholder:text-gray-300 font-mono uppercase tracking-wider"
            autoComplete="username"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="PASSWORD"
            className="w-full bg-white border-2 border-brand-black p-4 rounded-full text-sm font-bold focus:outline-none placeholder:text-gray-300 font-mono uppercase tracking-wider"
            autoComplete="current-password"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full editorial-button py-5 uppercase tracking-[0.2em] text-sm disabled:opacity-50"
          >
            {loading ? 'Entering...' : 'Enter The Club'}
          </button>
        </form>

        <p className="text-center">
          <button
            type="button"
            onClick={() => setShowRegister(true)}
            className="font-mono text-[11px] uppercase tracking-widest text-brand-black/70 hover:text-brand-black underline"
          >
            Create account
          </button>
        </p>

        <div className="editorial-card p-4 mt-4">
          <p className="text-[9px] font-mono font-bold text-gray-500 uppercase tracking-widest mb-1">Demo</p>
          <p className="text-xs font-mono">suhanimathur / 1234</p>
        </div>
      </div>
    </div>
  );
}
