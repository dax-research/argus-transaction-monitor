# Animation Types Available for All Pages

This guide explains all the animation types you can add to your pages.

## 🎬 Animation Categories

### 1. **Page Load Animations**
Elements animate when the page loads:
- **Fade In**: Elements fade in smoothly
- **Fade In Up**: Elements slide up while fading in
- **Fade In Down**: Elements slide down while fading in
- **Fade In Left/Right**: Elements slide from sides while fading in
- **Scale In**: Elements zoom in from small to full size

**Usage:**
```html
<div class="animate-on-load">This will fade in on page load</div>
```

### 2. **Scroll-Triggered Animations**
Elements animate when they scroll into view (Intersection Observer):
- Automatically triggers when element enters viewport
- Works with `.animate-on-scroll` class
- Staggered delays for multiple elements

**Usage:**
```html
<div class="animate-on-scroll">Animates when scrolled into view</div>
```

### 3. **Staggered Animations**
Perfect for lists, tables, and card grids:
- Each item animates with a delay after the previous
- Creates a cascading effect
- Used for: table rows, card lists, navigation items

**Usage:**
```html
<div class="stagger-animation">Item 1</div>
<div class="stagger-animation">Item 2</div>
<div class="stagger-animation">Item 3</div>
```

### 4. **Number Counter Animations**
Animate numbers counting up to target values:
- Smooth counting animation
- Supports currency, percentages, decimals
- Automatic prefix/suffix support

**Usage:**
```html
<div class="kpi-value" 
     data-counter="142.5" 
     data-prefix="$" 
     data-suffix="M">$0M</div>
```

### 5. **Ripple Button Effects**
Click animations on buttons:
- Material Design-style ripple effect
- Automatically applied to buttons with `.ripple-button`
- Works on all buttons by default

**Usage:**
```html
<button class="ripple-button">Click me!</button>
```

### 6. **Live Data Indicators**
Pulsing animations for real-time data:
- Green pulsing dot for "live" status
- Continuous pulse animation

**Usage:**
```html
<span class="live-indicator"></span> Live Feed
```

### 7. **Loading States**
- **Spinner**: Rotating loading spinner
- **Skeleton Loaders**: Shimmer effect for loading placeholders

**Usage:**
```html
<div class="loading-spinner"></div>
<div class="skeleton" style="height: 20px; width: 100%;"></div>
```

### 8. **Hover Effects**
- **Glow Effect**: Elements glow on hover
- **Scale**: Elements slightly scale up on hover
- **3D Tilt**: Cards tilt based on mouse position

**Usage:**
```html
<div class="hover-glow">Hover to see glow</div>
```

### 9. **Status Change Animations**
- **Bounce In**: Elements bounce when appearing (for status changes)
- **Shake**: Shake animation for errors
- **Pulse**: Quick pulse for alerts/notifications

**Usage (via JavaScript):**
```javascript
AnimationUtils.shakeElement(element); // Shake on error
AnimationUtils.pulseElement(element); // Pulse on alert
```

### 10. **Table Row Animations**
Table rows slide up with staggered delays:
- Automatic on all `.data-table tbody tr` elements
- Smooth slide-up animation
- Staggered timing

### 11. **Card Animations**
Cards have built-in animations:
- KPI cards: Scale in with staggered delays
- Regular cards: Fade in up animation
- Feature cards: 3D tilt on hover (landing page)

### 12. **Navigation Animations**
- Sidebar: Fades in from left
- Top bar: Fades in from top
- Nav links: Smooth transitions on hover/active

## 📋 How to Add Animations to Your Pages

### Step 1: Include the Animation Files

Add these to your HTML `<head>` and before `</body>`:

```html
<head>
    <!-- Add this after your existing CSS -->
    <link rel="stylesheet" href="css/animations.css">
</head>

<body>
    <!-- Your content -->
    
    <!-- Add this before closing body tag, after other scripts -->
    <script src="js/animations.js"></script>
</body>
```

### Step 2: Add Animation Classes

Simply add CSS classes to elements you want to animate:

```html
<!-- Scroll animation -->
<div class="card animate-on-scroll">
    <h3>This card animates when scrolled into view</h3>
</div>

<!-- Staggered list -->
<ul>
    <li class="stagger-animation">Item 1</li>
    <li class="stagger-animation">Item 2</li>
    <li class="stagger-animation">Item 3</li>
</ul>

<!-- Counter animation -->
<div class="kpi-value" 
     data-counter="1000" 
     data-prefix="$" 
     data-suffix="K">$0K</div>
```

### Step 3: Use JavaScript Functions (if needed)

For programmatic animations:

```javascript
// Animate new element when added to DOM
AnimationUtils.animateNewElement(newElement);

// Shake element (for errors)
AnimationUtils.shakeElement(errorElement);

// Pulse element (for alerts)
AnimationUtils.pulseElement(alertElement);

// Animate counter manually
AnimationUtils.animateCounter(element, targetValue, duration, prefix, suffix);
```

## 🎨 Pre-built Animated Components

### KPI Cards
Already animated! Cards in `.kpi-grid` automatically:
- Scale in on page load
- Staggered delays (0.1s, 0.2s, 0.3s, 0.4s)
- Hover effects included

### Tables
Table rows (`.data-table tbody tr`) automatically:
- Slide up with staggered delays
- Hover transitions

### Cards
Cards (`.card`) automatically:
- Fade in up on page load
- Smooth transitions

## 🎯 Recommended Animations by Page Type

### Dashboard Pages
- ✅ KPI cards (already animated)
- ✅ Counter animations for numbers
- ✅ Scroll animations for charts/cards
- ✅ Live indicator pulse

### Table/List Pages
- ✅ Staggered row animations
- ✅ Scroll-triggered animations for sections
- ✅ Hover effects on rows

### Forms
- ✅ Shake animation on validation errors
- ✅ Ripple effects on buttons
- ✅ Fade in for form fields

### Landing Pages
- ✅ Scroll-triggered animations
- ✅ Staggered feature cards
- ✅ Counter animations for stats

## ⚡ Performance Tips

1. **Use CSS animations** when possible (better performance)
2. **Avoid animating too many elements** at once (max 20-30)
3. **Use `will-change`** for frequently animated elements
4. **Respect `prefers-reduced-motion`** (already included)

## 🔧 Customization

All animations use CSS custom properties and can be customized:

```css
/* Change animation duration */
.animate-on-scroll {
    transition-duration: 0.8s; /* Default is 0.6s */
}

/* Change stagger delay */
.stagger-animation {
    transition-delay: 150ms; /* Adjust per element */
}
```

## 📱 Accessibility

- ✅ Respects `prefers-reduced-motion` media query
- ✅ Animations don't interfere with keyboard navigation
- ✅ Smooth and non-jarring transitions

## 🎬 Animation Examples

### Example 1: Animated Dashboard Section
```html
<div class="card animate-on-scroll">
    <h3>Recent Activity</h3>
    <div class="stagger-animation">Activity 1</div>
    <div class="stagger-animation">Activity 2</div>
</div>
```

### Example 2: Animated Stats
```html
<div class="stat-card">
    <div class="stat-label">Total Revenue</div>
    <div class="stat-value" 
         data-counter="50000" 
         data-prefix="$">$0</div>
</div>
```

### Example 3: Error Handling
```javascript
if (error) {
    const errorDiv = document.querySelector('.error-message');
    AnimationUtils.shakeElement(errorDiv);
}
```

---

**Need more specific examples?** Check the updated `dashboard.html` to see animations in action!

