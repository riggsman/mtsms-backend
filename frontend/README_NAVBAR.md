# Responsive Navbar Component

A fully responsive navbar component that works on all screen sizes and displays all elements properly.

## Features

✅ **Fully Responsive** - Works on mobile, tablet, and desktop
✅ **All Elements Visible** - All menu items are accessible on all screen sizes
✅ **Mobile-First Design** - Hamburger menu for mobile devices
✅ **Smooth Animations** - Transitions and hover effects
✅ **Accessibility** - ARIA labels and keyboard navigation support
✅ **Role-Based Menu** - Shows menu items based on user role

## Files Created

1. **Navbar.jsx** - React component
2. **Navbar.vue** - Vue component  
3. **Navbar.html** - Plain HTML/JS version
4. **Navbar.css** - Responsive styles (shared by all versions)

## Responsive Breakpoints

- **Desktop (≥1024px)**: Full horizontal menu with all items visible
- **Tablet (768px - 1023px)**: Compact menu with slightly smaller items
- **Mobile (<768px)**: Hamburger menu with vertical dropdown
- **Small Mobile (<480px)**: Optimized spacing and font sizes
- **Extra Small (<360px)**: Further optimized for tiny screens

## Usage

### React
```jsx
import Navbar from './components/Navbar';
import './components/Navbar.css';

function App() {
  const user = { username: 'admin', role: 'admin' };
  
  const handleLogout = () => {
    // Logout logic
  };

  return <Navbar user={user} onLogout={handleLogout} />;
}
```

### Vue
```vue
<template>
  <Navbar :user="user" :onLogout="handleLogout" />
</template>

<script>
import Navbar from './components/Navbar.vue';

export default {
  components: { Navbar },
  data() {
    return {
      user: { username: 'admin', role: 'admin' }
    };
  },
  methods: {
    handleLogout() {
      // Logout logic
    }
  }
};
</script>
```

### Plain HTML
Simply include the HTML file and link the CSS:
```html
<link rel="stylesheet" href="components/Navbar.css">
<!-- Include Navbar.html content -->
```

## Menu Items

The navbar automatically filters menu items based on user role:
- **admin/staff**: Full access to most features
- **teacher**: Courses, schedules, assignments, announcements
- **student**: Schedules, assignments, announcements, complaints
- **parent**: Announcements, complaints
- **super_admin/system_***: All features including system admin

## Customization

### Colors
Edit the gradient in `Navbar.css`:
```css
.navbar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Menu Items
Modify the `menuItems` array in the component to add/remove items.

### Breakpoints
Adjust breakpoints in the CSS media queries:
- `@media (max-width: 1024px)` - Tablet
- `@media (max-width: 768px)` - Mobile
- `@media (max-width: 480px)` - Small mobile

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Notes

- The navbar is sticky (stays at top when scrolling)
- Menu closes automatically when clicking outside on mobile
- Menu closes when window is resized to desktop size
- All menu items remain accessible via hamburger menu on mobile
- User info is hidden on mobile to save space (logout button remains visible)
