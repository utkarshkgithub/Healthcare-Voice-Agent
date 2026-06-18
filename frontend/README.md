# 🏥 HealthAI Frontend

> An AI-powered healthcare platform built with the Linear/Modern design system

![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript)
![Tailwind](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwind-css)
![Vite](https://img.shields.io/badge/Vite-8.1-646CFF?logo=vite)

## ✨ Features

- 🎨 **Stunning UI**: Linear/Modern design with cinematic animations
- 🔐 **Authentication**: Login/Signup with protected routes
- 📊 **Dashboard**: Real-time health metrics and stats
- 💬 **AI Chat**: Voice agent with conversation history
- 🌙 **Dark Theme**: Deep space aesthetic with ambient lighting
- ⚡ **Fast**: Vite + React 19 for instant HMR
- 📱 **Responsive**: Desktop-first, mobile-ready (in progress)

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
# http://localhost:5173
```

## 📸 Screenshots

### Login Page
- Glass-morphic authentication card
- Animated gradient background
- Smooth hover effects

### Dashboard
- Health stats overview
- Recent consultations
- Upcoming appointments
- Health metrics panel

### Voice Agent
- Real-time AI chat
- Voice recording toggle
- Conversation history
- Typing indicators

## 🎨 Design System

### Colors
```css
Background Deep:  #020203
Background Base:  #050506
Accent:          #5E6AD2
Foreground:      #EDEDEF
```

### Typography
- Font: Inter
- Gradient headlines
- Clean hierarchy

### Components
- Glass-morphic cards
- Multi-layer shadows
- Animated backgrounds
- Smooth transitions (200-300ms)

## 🏗️ Project Structure

```
src/
├── components/
│   └── Layout/
│       ├── Background.tsx    # Animated ambient background
│       └── Navbar.tsx         # Navigation with profile menu
├── pages/
│   ├── Login.tsx              # Authentication
│   ├── Signup.tsx             # Registration
│   ├── Dashboard.tsx          # Patient overview
│   └── VoiceAgent.tsx         # AI chat interface
├── utils/
│   └── api.ts                 # API client & endpoints
├── App.tsx                    # Router configuration
├── main.tsx                   # Entry point
└── index.css                  # Global styles
```

## 🔧 Tech Stack

| Category | Technology |
|----------|-----------|
| **Framework** | React 19 |
| **Language** | TypeScript 6.0 |
| **Styling** | Tailwind CSS |
| **Animation** | Framer Motion |
| **Routing** | React Router v7 |
| **Icons** | Lucide React |
| **Build Tool** | Vite 8.1 |

## 📝 Available Scripts

```bash
# Development
npm run dev          # Start dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Run ESLint
```

## 🔌 Backend Integration

### Setup
1. Copy `.env.example` to `.env`
2. Update `VITE_API_BASE_URL` with your backend URL
3. API client is in `src/utils/api.ts`

### Required Endpoints
```typescript
POST   /api/auth/login
POST   /api/auth/signup
GET    /api/dashboard/stats
GET    /api/consultations/recent
GET    /api/appointments/upcoming
GET    /api/health/metrics
POST   /api/chat/send
GET    /api/chat/history
WS     /ws  (WebSocket for real-time chat)
```

## 🎯 Pages & Routes

| Route | Page | Auth Required |
|-------|------|--------------|
| `/login` | Login | No |
| `/signup` | Signup | No |
| `/dashboard` | Dashboard | Yes |
| `/voice-agent` | Voice Agent | Yes |
| `/` | Redirect to Dashboard | Yes |

## 🎨 Customization

### Modify Colors
Edit `tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      accent: {
        DEFAULT: '#5E6AD2', // Change accent color
      }
    }
  }
}
```

### Change Animations
Edit `framer-motion` configs in components:
```typescript
animate={{ y: [0, -20, 0] }}
transition={{ duration: 8 }}
```

## 🧪 Demo

See [DEMO.md](./DEMO.md) for detailed demo flow and test scenarios.

## 🐛 Known Issues

- [ ] Voice recording needs Web Audio API integration
- [ ] Auth is mocked (pending backend connection)
- [ ] Mobile responsive layout needs enhancement
- [ ] Some npm package vulnerabilities (run `npm audit fix`)

## 🔮 Roadmap

- [ ] Connect to real backend API
- [ ] Implement voice recording with Web Audio API
- [ ] Add WebSocket for real-time chat
- [ ] Add form validation & error handling
- [ ] Add loading states & skeletons
- [ ] Mobile hamburger menu
- [ ] Add more pages (Profile, Settings, Medical Records)
- [ ] Add unit tests with Vitest
- [ ] Add E2E tests with Playwright
- [ ] Add accessibility improvements

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit PR

## 📄 License

Private project - All rights reserved

## 👨‍💻 Author

Built with ❤️ for HealthAI

---
