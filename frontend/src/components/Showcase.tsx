/**
 * Component Showcase
 * 
 * This file demonstrates all reusable design patterns and components
 * from the HealthAI design system. Use as reference when building new features.
 */

import { Activity, Heart, Brain, Zap } from 'lucide-react';

export default function Showcase() {
  return (
    <div className="min-h-screen bg-background-base p-8 space-y-12">
      {/* Typography */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Typography</h2>
        <div className="space-y-4">
          <h1 className="text-7xl font-semibold text-gradient">Display Heading</h1>
          <h2 className="text-5xl font-semibold text-gradient">H1 Heading</h2>
          <h3 className="text-3xl font-semibold text-foreground">H2 Heading</h3>
          <h4 className="text-xl font-semibold text-foreground">H3 Heading</h4>
          <p className="text-lg text-foreground">Body Large Text</p>
          <p className="text-base text-foreground-muted">Body Text</p>
          <p className="text-sm text-foreground-subtle">Small Text</p>
          <p className="text-xs font-mono tracking-widest text-foreground-subtle">LABEL TEXT</p>
        </div>
      </section>

      {/* Buttons */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Buttons</h2>
        <div className="flex flex-wrap gap-4">
          <button className="btn-primary">Primary Button</button>
          <button className="btn-secondary">Secondary Button</button>
          <button className="btn-primary" disabled>Disabled Button</button>
          <button className="p-3 rounded-lg bg-white/[0.05] hover:bg-white/[0.08] transition-colors">
            <Activity className="w-5 h-5 text-foreground" />
          </button>
        </div>
      </section>

      {/* Cards */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Cards</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Glass Card */}
          <div className="card-glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-foreground mb-2">Glass Card</h3>
            <p className="text-foreground-muted text-sm">
              Translucent background with subtle border
            </p>
          </div>

          {/* Hover Card */}
          <div className="card-glass card-glass-hover rounded-2xl p-6 cursor-pointer">
            <h3 className="text-lg font-semibold text-foreground mb-2">Hover Card</h3>
            <p className="text-foreground-muted text-sm">
              Hover to see enhanced shadow and border
            </p>
          </div>

          {/* Gradient Card */}
          <div className="bg-gradient-to-br from-accent/20 to-purple-600/20 border border-accent/30 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-foreground mb-2">Accent Card</h3>
            <p className="text-foreground-muted text-sm">
              With gradient background and accent border
            </p>
          </div>
        </div>
      </section>

      {/* Stats Cards */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Stat Cards</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { label: 'Consultations', value: '12', icon: Activity, color: 'from-blue-500 to-cyan-500' },
            { label: 'Heart Rate', value: '72', icon: Heart, color: 'from-red-500 to-pink-500' },
            { label: 'Mental Health', value: 'Good', icon: Brain, color: 'from-purple-500 to-indigo-500' },
            { label: 'Energy Level', value: 'High', icon: Zap, color: 'from-yellow-500 to-orange-500' },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="card-glass rounded-2xl p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-2xl font-semibold text-foreground">{stat.value}</span>
                </div>
                <h3 className="text-foreground-muted text-sm">{stat.label}</h3>
              </div>
            );
          })}
        </div>
      </section>

      {/* Form Inputs */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Form Inputs</h2>
        <div className="max-w-md space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Text Input
            </label>
            <input
              type="text"
              placeholder="Enter text..."
              className="input-field w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              With Icon
            </label>
            <div className="relative">
              <Activity className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-foreground-subtle" />
              <input
                type="text"
                placeholder="With icon..."
                className="input-field w-full pl-11"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Textarea
            </label>
            <textarea
              placeholder="Enter message..."
              rows={4}
              className="input-field w-full resize-none"
            />
          </div>
        </div>
      </section>

      {/* Badges */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Badges</h2>
        <div className="flex flex-wrap gap-3">
          <span className="text-xs px-3 py-1 rounded-full bg-accent/20 text-accent border border-accent/30">
            Primary
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
            Success
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30">
            Warning
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
            Error
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-white/10 text-foreground-muted border border-white/10">
            Neutral
          </span>
        </div>
      </section>

      {/* List Items */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">List Items</h2>
        <div className="max-w-2xl space-y-3">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="bg-white/[0.02] hover:bg-white/[0.05] rounded-xl p-4 border border-white/[0.06] 
                       hover:border-white/[0.1] transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-foreground font-medium mb-1">List Item {item}</h3>
                  <p className="text-sm text-foreground-muted">Description of the item</p>
                </div>
                <Activity className="w-5 h-5 text-accent" />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Gradient Text */}
      <section>
        <h2 className="text-2xl font-semibold text-foreground mb-6">Gradient Text</h2>
        <div className="space-y-4">
          <h1 className="text-6xl font-semibold text-gradient">
            Gradient Heading
          </h1>
          <h2 className="text-4xl font-semibold text-gradient-accent">
            Animated Accent Gradient
          </h2>
        </div>
      </section>
    </div>
  );
}
