import { motion } from 'framer-motion';
import { Calendar, MessageSquare, Activity, TrendingUp, Clock, Heart, Brain, Stethoscope } from 'lucide-react';
import Navbar from '../components/Layout/Navbar';
import Background from '../components/Layout/Background';

export default function Dashboard() {
  const stats = [
    { label: 'Consultations', value: '12', icon: MessageSquare, change: '+2 this week', color: 'from-blue-500 to-cyan-500' },
    { label: 'Appointments', value: '3', icon: Calendar, change: 'Next: Tomorrow', color: 'from-purple-500 to-pink-500' },
    { label: 'Health Score', value: '87', icon: Activity, change: '+5 from last month', color: 'from-green-500 to-emerald-500' },
    { label: 'Active Plan', value: 'Premium', icon: TrendingUp, change: 'Expires in 45 days', color: 'from-orange-500 to-red-500' },
  ];

  const recentConsultations = [
    { id: 1, date: '2026-07-05', time: '14:30', reason: 'General checkup', status: 'Completed', priority: 'Low' },
    { id: 2, date: '2026-07-03', time: '10:15', reason: 'Headache symptoms', status: 'Completed', priority: 'Medium' },
    { id: 3, date: '2026-07-01', time: '16:45', reason: 'Follow-up', status: 'Completed', priority: 'Low' },
  ];

  const upcomingAppointments = [
    { id: 1, date: '2026-07-07', time: '09:00', doctor: 'Dr. Sarah Johnson', specialty: 'Cardiologist', type: 'In-person' },
    { id: 2, date: '2026-07-10', time: '15:30', doctor: 'Dr. Michael Chen', specialty: 'Neurologist', type: 'Video Call' },
  ];

  const healthMetrics = [
    { label: 'Heart Rate', value: '72 bpm', icon: Heart, status: 'Normal' },
    { label: 'Blood Pressure', value: '120/80', icon: Activity, status: 'Optimal' },
    { label: 'Mental Health', value: 'Good', icon: Brain, status: 'Stable' },
    { label: 'Last Checkup', value: '15 days ago', icon: Stethoscope, status: 'Recent' },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <div className="min-h-screen">
      <Background />
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-semibold text-gradient mb-2">Welcome back, Patient</h1>
          <p className="text-foreground-muted text-lg">Here's your health overview for today</p>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                variants={itemVariants}
                whileHover={{ y: -4 }}
                className="card-glass rounded-2xl p-6 card-glass-hover transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-2xl font-semibold text-foreground">{stat.value}</span>
                </div>
                <h3 className="text-foreground-muted text-sm mb-1">{stat.label}</h3>
                <p className="text-xs text-foreground-subtle">{stat.change}</p>
              </motion.div>
            );
          })}
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Consultations */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="lg:col-span-2 card-glass rounded-2xl p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-foreground">Recent Consultations</h2>
              <button className="text-sm text-accent hover:text-accent-bright transition-colors">
                View All
              </button>
            </div>
            
            <div className="space-y-3">
              {recentConsultations.map((consultation) => (
                <div
                  key={consultation.id}
                  className="bg-white/[0.02] hover:bg-white/[0.05] rounded-xl p-4 border border-white/[0.06] transition-all duration-200"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-foreground-subtle" />
                      <span className="text-sm text-foreground-muted">{consultation.date} at {consultation.time}</span>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      consultation.priority === 'Medium' 
                        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' 
                        : 'bg-green-500/20 text-green-400 border border-green-500/30'
                    }`}>
                      {consultation.priority}
                    </span>
                  </div>
                  <p className="text-foreground font-medium">{consultation.reason}</p>
                  <p className="text-xs text-foreground-subtle mt-1">{consultation.status}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Health Metrics */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="card-glass rounded-2xl p-6"
          >
            <h2 className="text-xl font-semibold text-foreground mb-6">Health Metrics</h2>
            
            <div className="space-y-4">
              {healthMetrics.map((metric) => {
                const Icon = metric.icon;
                return (
                  <div key={metric.label} className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white/[0.05] flex items-center justify-center border border-white/[0.06]">
                      <Icon className="w-5 h-5 text-accent" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-foreground-muted">{metric.label}</p>
                      <p className="text-foreground font-medium">{metric.value}</p>
                    </div>
                    <span className="text-xs text-green-400">{metric.status}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>

        {/* Upcoming Appointments */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-6 card-glass rounded-2xl p-6"
        >
          <h2 className="text-xl font-semibold text-foreground mb-6">Upcoming Appointments</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {upcomingAppointments.map((appointment) => (
              <div
                key={appointment.id}
                className="bg-gradient-to-br from-white/[0.08] to-white/[0.02] rounded-xl p-5 border border-white/[0.06] 
                         hover:border-accent/30 transition-all duration-300"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-foreground font-semibold text-lg">{appointment.doctor}</p>
                    <p className="text-sm text-foreground-muted">{appointment.specialty}</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-accent/20 text-accent border border-accent/30">
                    {appointment.type}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-foreground-subtle">
                  <Calendar className="w-4 h-4" />
                  <span>{appointment.date} at {appointment.time}</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
