import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, MessageSquare, LogOut, User } from 'lucide-react';
import { authApi } from '../../utils/api';
import Logo from './Logo';

export default function Navbar() {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [userName, setUserName] = useState(() => localStorage.getItem('user_name') || 'Patient User');
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem('user_email') || 'patient@healthai.com');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const userId = localStorage.getItem('user_id');
    if (userId) {
      authApi.getMe(userId)
        .then((data) => {
          if (data.name) {
            setUserName(data.name);
            localStorage.setItem('user_name', data.name);
          }
          if (data.email) {
            setUserEmail(data.email);
            localStorage.setItem('user_email', data.email);
          }
        })
        .catch((err) => {
          console.error('Failed to fetch profile details:', err);
        });
    }
  }, []);

  const handleLogout = () => {
    authApi.logout();
    navigate('/login');
  };


  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/voice-agent', label: 'Voice Agent', icon: MessageSquare },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.06] backdrop-blur-xl bg-background-base/80">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Logo size="md" linkTo="/dashboard" />

          {/* Nav Links */}
          <div className="flex items-center gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                    flex items-center gap-2
                    ${active 
                      ? 'text-foreground bg-white/[0.08]' 
                      : 'text-foreground-muted hover:text-foreground hover:bg-white/[0.05]'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                  {active && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute inset-0 bg-white/[0.08] rounded-lg border border-white/[0.1]"
                      style={{ zIndex: -1 }}
                      transition={{ type: 'spring', duration: 0.5 }}
                    />
                  )}
                </Link>
              );
            })}
          </div>

          {/* Profile or Login */}
          {localStorage.getItem('token') ? (
            <div className="relative">
              <button
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="
    flex h-10 w-10 items-center justify-center
    rounded-full
    border border-white/10
    bg-accent
    shadow-lg shadow-accent/20
    transition-all duration-200
    hover:scale-105
  "
              >
                <User className="w-5 h-5 text-white" />
              </button>
  
              <AnimatePresence>
                {showProfileMenu && (
                  <>
                    {/* Backdrop */}
                    <div 
                      className="fixed inset-0 z-40" 
                      onClick={() => setShowProfileMenu(false)}
                    />
                    
                    {/* Menu */}
                    <motion.div
                      initial={{ opacity: 0, y: -10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -10, scale: 0.95 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-48 card-glass rounded-xl shadow-2xl overflow-hidden z-50"
                    >
                      <div className="p-3 border-b border-white/[0.06]">
                        <p className="text-sm font-medium text-foreground">{userEmail}</p>
                      </div>
                      
                      <button
                        onClick={handleLogout}
                        className="w-full px-3 py-2 text-left text-sm text-foreground-muted hover:text-foreground 
                                 hover:bg-white/[0.05] transition-colors duration-150 flex items-center gap-2"
                      >
                        <LogOut className="w-4 h-4" />
                        Logout
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-sm font-medium text-foreground hover:text-white transition-colors">
                Log in
              </Link>
              <Link to="/signup" className="text-sm font-medium bg-white text-black px-4 py-2 rounded-full hover:bg-neutral-200 transition-colors">
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
