# FlashForgeDash UI Redesign Specification

**Inspiration:** Modern IoT/SaaS dashboards (Phoenix, Worklio style)
**Design System:** Dark theme with elevated cards and vibrant accents
**Date:** 2026-01-28

---

## Design Principles

### 1. **Information Architecture**
```
┌─────────────────────────────────────────────────────────┐
│ Header (Compact, Sticky)                                │
│ Status • IP • Quick Links • Settings                    │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│   PRIMARY CONTENT    │    SIDEBAR                       │
│   • Camera (Large)   │    • Status Card                 │
│   • Progress Card    │    • Temperature Card            │
│                      │    • Quick Actions               │
│                      │    • File Management             │
│                      │                                  │
└──────────────────────┴──────────────────────────────────┘
```

### 2. **Color Palette**

**Base Colors (Dark Theme)**
- `bg-primary`: #0F172A (slate-900)
- `bg-secondary`: #1E293B (slate-800)
- `bg-elevated`: #334155 (slate-700)
- `border`: #475569 (slate-600)
- `text-primary`: #F1F5F9 (slate-100)
- `text-secondary`: #94A3B8 (slate-400)

**Accent Colors**
- `accent-primary`: #F97316 (orange-500) - Active printing, nozzle
- `accent-secondary`: #3B82F6 (blue-500) - Bed, info
- `success`: #10B981 (emerald-500) - Connected, complete
- `warning`: #F59E0B (amber-500) - Paused, heating
- `danger`: #EF4444 (red-500) - Error, emergency stop

**Status Colors**
- Idle: `#22C55E` (green-500)
- Printing: `#F97316` (orange-500) with pulse
- Paused: `#EAB308` (yellow-500)
- Complete: `#3B82F6` (blue-500)
- Error: `#EF4444` (red-500)
- Disconnected: `#6B7280` (gray-500)

### 3. **Typography**

```css
/* Headers */
.hero: text-2xl font-bold (24px)
.h1: text-xl font-semibold (20px)
.h2: text-lg font-semibold (18px)
.h3: text-base font-medium (16px)

/* Body */
.body: text-sm (14px)
.caption: text-xs (12px)
.micro: text-[10px] (10px)

/* Special */
.metric: text-4xl font-bold (36px) - For key numbers
.mono: font-mono - For numerical data
```

### 4. **Component Patterns**

#### Card Component
```html
<div class="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg hover:border-slate-600 transition-colors">
  <h3 class="text-lg font-semibold mb-4">Card Title</h3>
  <!-- Content -->
</div>
```

#### Status Badge
```html
<span class="inline-flex items-center gap-2 px-3 py-1 bg-slate-700 border border-slate-600 rounded-full text-sm">
  <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
  Connected
</span>
```

#### Metric Display
```html
<div class="text-center">
  <div class="text-4xl font-bold text-orange-500">210°C</div>
  <div class="text-xs text-slate-400 mt-1">Nozzle Temp</div>
</div>
```

---

## Detailed Component Redesigns

### Header (Compact & Clean)

**Changes:**
- Reduce height from current to ~60px
- Move model site links to a dropdown menu (cleaner)
- Add breadcrumb-style navigation
- Subtle glassmorphism effect

```html
<header class="h-16 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
  <div class="flex items-center justify-between px-6 h-full">
    <!-- Left -->
    <div class="flex items-center gap-6">
      <h1 class="text-xl font-bold">FlashForge</h1>
      <div class="h-6 w-px bg-slate-700"></div>
      <span class="text-sm text-slate-400">Adventurer 3 • 192.168.1.200</span>
    </div>

    <!-- Center - Status Badge -->
    <div class="status-badge">
      <!-- Prominent status display -->
    </div>

    <!-- Right -->
    <div class="flex items-center gap-4">
      <button class="icon-button">Resources ▾</button> <!-- Model sites dropdown -->
      <button class="icon-button">⚙️</button>
    </div>
  </div>
</header>
```

---

### Main Layout (Card Grid)

**Structure:**
- Left column: 66% width (camera + progress)
- Right column: 33% width (stats + controls)
- Gap: 24px
- Cards have consistent padding (24px)

---

### Status Overview Card (NEW)

**Purpose:** At-a-glance printer status
**Position:** Top of right sidebar

**Contents:**
- Large status indicator with icon
- Current state (Idle/Printing/Paused/Error)
- Uptime or connection duration
- Quick reconnect button if disconnected

```
┌─────────────────────────────┐
│ Printer Status              │
│                             │
│   🟢  CONNECTED             │
│                             │
│   Uptime: 2h 34m            │
│   Last poll: 2s ago         │
│                             │
│   [Reconnect]               │
└─────────────────────────────┘
```

---

### Temperature Card (Redesigned)

**Changes:**
- Remove circular gauges (outdated pattern)
- Use linear progress bars with current/target
- Add temperature trend indicators (↑↗→↘↓)
- Material presets as chips/pills
- Manual controls in expandable section

**New Design:**

```
┌─────────────────────────────┐
│ Temperatures                │
│                             │
│ Nozzle          210°C / 210 │
│ ████████████████████░  100% │
│ ↗ Heating                   │
│                             │
│ Bed              60°C / 60  │
│ ████████████████████░  100% │
│ → At target                 │
│                             │
│ Quick Presets:              │
│ [PLA] [PETG] [ABS] [ASA]   │
│ [Cool Down]                 │
│                             │
│ ˅ Manual Control            │
└─────────────────────────────┘
```

---

### Camera Feed (Enhanced)

**Changes:**
- Larger aspect ratio control
- Overlay controls (instead of separate)
- Snapshot button
- Fullscreen toggle
- Recording indicator if active
- Timestamp overlay

```
┌─────────────────────────────────────┐
│ Live Feed                [⛶] [📷] │
│                                     │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │     CAMERA FEED             │   │
│  │                             │   │
│  │                             │   │
│  │  ⏺ REC  12:34:56  •  30fps │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

### Progress Card (Enhanced)

**Current Problems:**
- Progress bar is basic
- Time remaining format is unclear
- No ETA or time started info

**New Design:**

```
┌─────────────────────────────────────┐
│ Print Progress                      │
│                                     │
│            65%                      │
│ ██████████████░░░░░░░               │
│                                     │
│ benchy_final.gcode                  │
│                                     │
│ ⏱ Time Elapsed:    1h 23m          │
│ ⏰ Remaining:       45m             │
│ 🏁 ETA:            14:45            │
│                                     │
│ 📊 Layer 145/223                    │
│ 🧵 Filament: 24.3m / 35.1m         │
│                                     │
│ [Pause] [Cancel]                    │
└─────────────────────────────────────┘
```

---

### Controls Card (Reorganized)

**Changes:**
- Group by function type
- Use icon buttons for compactness
- Confirmation modals for dangerous actions
- Visual hierarchy (primary/secondary/danger)

**New Organization:**

```
┌─────────────────────────────┐
│ Quick Actions               │
│                             │
│ Print Control               │
│ [▶ Resume] [⏸ Pause]       │
│ [⏹ Cancel]                 │
│                             │
│ Printer                     │
│ [🏠 Home] [💡 LED] [🌀 Fan] │
│                             │
│ Position                    │
│ X: 125.4  Y: 63.2  Z: 5.8  │
│                             │
│ ─────────────────────       │
│                             │
│ 🛑 Emergency Stop           │
│                             │
└─────────────────────────────┘
```

---

### File Management (Unified)

**Keep current tab approach but refine:**
- Better visual states for tabs
- Drag & drop zone improvements
- File cards instead of dropdown
- Thumbnail previews if available

```
┌─────────────────────────────┐
│ [Upload New] [SD Card]      │
├─────────────────────────────┤
│                             │
│ Upload Mode:                │
│  ┌─────────────────────┐   │
│  │  📁 Drop file here  │   │
│  │  or click to browse │   │
│  └─────────────────────┘   │
│                             │
│ Selected: benchy.gcode      │
│ Size: 2.4 MB                │
│ Est. Time: 2h 15m           │
│ Layers: 223                 │
│                             │
│ [▶ Upload & Start Print]   │
│                             │
└─────────────────────────────┘
```

---

## Visual Improvements

### 1. **Shadows & Depth**
```css
/* Elevation levels */
.elevation-1: shadow-lg (0 10px 15px -3px rgb(0 0 0 / 0.1))
.elevation-2: shadow-xl (0 20px 25px -5px rgb(0 0 0 / 0.1))
.elevation-3: shadow-2xl (0 25px 50px -12px rgb(0 0 0 / 0.25))
```

### 2. **Transitions**
- All interactive elements: `transition-all duration-200`
- Hover states on cards: subtle border color change
- Button states: scale and color transitions

### 3. **Border Radius**
- Cards: `rounded-xl` (12px)
- Buttons: `rounded-lg` (8px)
- Small elements: `rounded-md` (6px)
- Pills/badges: `rounded-full`

### 4. **Spacing System**
- Card padding: `p-6` (24px)
- Section gaps: `gap-6` (24px)
- Element spacing: `space-y-4` (16px)
- Tight grouping: `gap-2` (8px)

### 5. **Icons**
- Use Heroicons or Lucide (consistent set)
- Size: 16px for inline, 20px for buttons, 24px for headers
- Stroke width: 2px
- Color: Inherit from parent with opacity

---

## Micro-interactions

### Temperature Trend Indicators
```javascript
// Show trend arrows based on rate of change
if (deltaTemp > 2) return '↗ Heating'
if (deltaTemp > 0.5) return '↑ Warming'
if (Math.abs(deltaTemp) < 0.5) return '→ At target'
if (deltaTemp < -2) return '↘ Cooling'
if (deltaTemp < -0.5) return '↓ Dropping'
```

### Progress Animations
- Smooth progress bar transitions
- Pulse effect when actively printing
- Color shift as print nears completion (orange → green gradient)

### Status Updates
- Toast notifications slide in from top-right
- Success: green border, check icon
- Error: red border, X icon
- Info: blue border, i icon

---

## Responsive Breakpoints

```css
/* Mobile: < 768px */
- Stack all cards vertically
- Camera full width
- Hide model site links
- Collapse controls into accordion

/* Tablet: 768px - 1024px */
- 2-column grid
- Camera + progress on left
- Sidebar cards stack on right

/* Desktop: > 1024px */
- 3-column grid option
- More horizontal space utilization
```

---

## Implementation Priority

### Phase 1: Foundation (Essential)
- [ ] Update color system to new palette
- [ ] Redesign header to compact version
- [ ] Implement card-based layout with proper shadows
- [ ] Update typography scale

### Phase 2: Components (High Impact)
- [ ] Redesign temperature card (linear bars + trends)
- [ ] Enhance progress card (more detail)
- [ ] Add status overview card
- [ ] Reorganize controls card

### Phase 3: Polish (Nice-to-have)
- [ ] Add micro-interactions and animations
- [ ] Implement camera overlays
- [ ] Add trend indicators
- [ ] Improve file management UI

### Phase 4: Advanced (Future)
- [ ] Add print history dashboard
- [ ] Temperature charts over time
- [ ] Mobile responsive optimization
- [ ] Print statistics cards

---

## Code Architecture

### Tailwind Config Extensions
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        slate: {
          850: '#1a2332', // Custom between 800 and 900
        }
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgb(0 0 0 / 0.15), 0 2px 4px -2px rgb(0 0 0 / 0.15)',
      }
    }
  }
}
```

### Component Structure
```
frontend/
├── index.html (main dashboard)
├── settings.html
├── styles/
│   └── custom.css (additional styles beyond Tailwind)
├── js/
│   ├── dashboard.js (main logic)
│   ├── components/
│   │   ├── temperature.js
│   │   ├── progress.js
│   │   └── camera.js
│   └── utils/
│       ├── api.js
│       └── formatting.js
```

---

## Accessibility Considerations

- Maintain WCAG AA contrast ratios (4.5:1 for text)
- Add ARIA labels to icon buttons
- Keyboard navigation for all controls
- Focus indicators on interactive elements
- Screen reader announcements for status changes

---

## Performance

- Lazy load camera feed
- Debounce status polling
- Use CSS transforms for animations (GPU accelerated)
- Optimize bundle size (consider custom Tailwind build)

---

## Design System Documentation

Create a living style guide page:
- Color swatches with hex codes
- Typography examples
- Button variants
- Card layouts
- Icon library
- Spacing examples

---

## Next Steps

1. **Review this spec** - Discuss priorities and modifications
2. **Create mockups** - Build HTML prototypes of key components
3. **Implement Phase 1** - Foundation updates
4. **User testing** - Test new layout with actual printing workflow
5. **Iterate** - Refine based on feedback

---

**Questions to Consider:**
- Do you want a sidebar layout or grid layout?
- Should temperature gauges stay (nostalgic) or switch to bars (modern)?
- How important is mobile/tablet support?
- Any branding/logo to incorporate?
- Preferred icon library?
