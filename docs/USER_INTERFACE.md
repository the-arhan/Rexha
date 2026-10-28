# Rexha — User Interface Design & Architecture

This document describes the visual design, PySide6 component hierarchy, styling tokens, and interaction flows for the Rexha desktop interface.

---

## 1. Visual Direction & Aesthetic

Rexha employs a dark, futuristic aesthetic with neon cyan and violet accents, deep charcoal slate surfaces, and clean typography:

- **Background Base:** Deep Obsidian (`#0F111A`)
- **Card / Surface Background:** Charcoal Slate (`#161926`) with subtle 1px border (`#2A2E45`)
- **Primary Accent (Cyan):** Electric Cyan (`#00F2FE` / `#4FACFE`)
- **Secondary Accent (Violet):** Neon Orchid (`#8A2387` / `#B33939` / `#7B2CBF`)
- **Text Main:** Pure Off-White (`#F0F4F8`)
- **Text Muted:** Soft Slate (`#8E9AA8`)
- **Status Colors:**
  - `Sleeping`: Soft Violet-Slate (`#6B7280`)
  - `Listening`: Pulsing Cyan (`#00F2FE`)
  - `Thinking`: Amber Glow (`#F59E0B`)
  - `Executing`: Neon Blue (`#3B82F6`)
  - `Success`: Emerald Green (`#10B981`)
  - `Error`: Crimson Alert (`#EF4444`)

---

## 2. Component Hierarchy

```
QApplication
│
├── SystemTrayController (QSystemTrayIcon)
│   ├── Tray Icon (status-aware)
│   └── Tray Context Menu (Open, Mute Mic, Settings, Quit)
│
├── FloatingWidget (Frameless, Always-on-Top QWidget)
│   ├── StatusBadge (Pill with state dot and text: "Sleeping...")
│   ├── LevelMeter (Subtle audio activity glow bar)
│   └── ExpandButton (Quick click to toggle interaction drawer)
│
└── InteractionPanel (Drawer attached or positioned beside widget)
    ├── Header Bar
    │   ├── Brand & State Badge ("REXHA: LISTENING")
    │   ├── Mic Status Icon (Active/Muted)
    │   └── Collapse / Close Button
    ├── ConversationView (QScrollArea / QListWidget)
    │   ├── User Message Bubbles
    │   └── Assistant Response Cards (Status, Plan Steps, Markdown output)
    ├── ConfirmationBanner (QFrame, shown dynamically for Tier-2 actions)
    │   ├── Action Description & Parameters
    │   ├── "Approve & Execute" Button
    │   └── "Cancel" Button
    └── InputBar
        ├── CommandLineEdit (Text input with placeholder: "Speak or type a command...")
        ├── MicToggleButton (Quick voice activation button)
        └── SubmitButton
```

---

## 3. Window Behavior & Interactions

1. **Draggable Positioning:**
   - The user can click and drag anywhere on the header or compact widget to move Rexha across displays.
   - Screen bounds checking ensures the widget never gets dragged off-screen.
   - On release, the widget coordinates `(x, y)` are saved to SQLite.
2. **Smooth Expansion & Collapse:**
   - Transitioning between the compact resting pill and the expanded panel uses smooth `QPropertyAnimation` on geometry/height without lagging command processing.
3. **Always-On-Top Toggle:**
   - Uses `Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool` so it floats gracefully above full-screen editors and IDEs without showing an intrusive taskbar button if configured as a tool.
4. **Follow-Up Collapse:**
   - A `QTimer` tracks inactivity in the `FOLLOW_UP` state (default: 30 seconds). When time expires without interaction, it smoothly collapses to the `SLEEPING` state.
