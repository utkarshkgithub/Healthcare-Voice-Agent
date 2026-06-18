import { motion } from 'framer-motion';

export default function Background() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Base gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,#0a0a0f_0%,#050506_50%,#020203_100%)]" />
      
      {/* Noise texture */}
      <div 
        className="absolute inset-0 opacity-[0.015]" 
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Animated gradient blobs */}
      <motion.div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[1400px] rounded-full blur-[150px] opacity-25"
        style={{ background: '#5E6AD2' }}
        animate={{
          y: [0, -20, 0],
          rotate: [0, 1, 0],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      
      <motion.div
        className="absolute top-1/4 -left-48 w-[600px] h-[800px] rounded-full blur-[120px] opacity-15"
        style={{ background: 'linear-gradient(135deg, #9333ea 0%, #ec4899 100%)' }}
        animate={{
          y: [0, 30, 0],
          x: [0, 20, 0],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      
      <motion.div
        className="absolute top-1/3 -right-32 w-[500px] h-[700px] rounded-full blur-[100px] opacity-12"
        style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #5E6AD2 100%)' }}
        animate={{
          y: [0, -25, 0],
          x: [0, -15, 0],
        }}
        transition={{
          duration: 9,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Grid overlay */}
      <div 
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />
    </div>
  );
}
