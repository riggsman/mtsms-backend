# Main Layout Structure - Green Theme

## Overview
The main layout of the frontend project uses a **green color theme** (`#4CAF50`, `#2e7d32`, `#1b5e20`) with a clean, modern design.

## Layout Components

### 1. **MainLayout.jsx** - Main Layout Wrapper
The primary layout component that wraps all pages.

**Structure:**
```
MainLayout
├── Navbar (Purple gradient header)
├── Main Content Area (Green-themed background)
│   └── Content Wrapper (White content sections with green accents)
└── Footer (Green gradient footer)
```

**Features:**
- Green gradient background (`#f0f9f4` → `#e8f5e9` → `#f1f8f4`)
- Green top accent bar (4px solid green line)
- White content sections with green left border
- Green footer with dark green gradient

### 2. **App.jsx** - Root Application Component
The main application entry point that uses MainLayout.

**Features:**
- User authentication state management
- Logout handling
- Loading screen with green spinner

### 3. **Navbar.jsx** - Navigation Bar
The top navigation (currently purple, can be customized to green).

## Color Scheme

### Primary Green Colors
- **Light Green**: `#4CAF50` - Buttons, accents
- **Medium Green**: `#45a049` - Button hover states
- **Dark Green**: `#2e7d32` - Headers, footer
- **Darker Green**: `#1b5e20` - Footer gradient
- **Light Background**: `#f0f9f4`, `#e8f5e9` - Page backgrounds

### Usage in Components
- **Edit Buttons**: `#4CAF50` background
- **Section Borders**: `#4CAF50` left border (4px)
- **Footer**: `#2e7d32` to `#1b5e20` gradient
- **Top Accent**: `#4CAF50` horizontal line

## File Structure

```
frontend/
├── components/
│   ├── MainLayout.jsx      # Main layout wrapper
│   ├── MainLayout.css      # Green theme styles
│   ├── App.jsx             # Root app component
│   ├── App.css             # App-specific styles
│   ├── Navbar.jsx          # Navigation component
│   ├── Navbar.css          # Navbar styles (purple)
│   └── [Other components]
└── styles/
    └── [Global styles]
```

## Usage Example

```jsx
import MainLayout from './components/MainLayout';
import LecturerManagement from './components/LecturerManagement';

function App() {
  const user = { username: 'admin', role: 'admin' };
  
  return (
    <MainLayout user={user} onLogout={handleLogout}>
      <LecturerManagement />
    </MainLayout>
  );
}
```

## Layout Features

### 1. **Green Theme Background**
- Subtle green gradient background
- Light green tones for a fresh, modern look

### 2. **Content Sections**
- White background for content
- Green left border accent (4px)
- Soft shadow with green tint
- Rounded corners (8px)

### 3. **Footer**
- Dark green gradient (`#2e7d32` → `#1b5e20`)
- White text
- Centered content
- Links with hover effects

### 4. **Top Accent Bar**
- Fixed 4px green line at the top
- Green gradient colors
- Always visible

## Responsive Design

- **Desktop**: Full layout with sidebar (if needed)
- **Tablet**: Adjusted padding and spacing
- **Mobile**: Stacked layout, reduced padding
- **Print**: Footer and accent bar hidden

## Customization

To change the green theme colors, update these CSS variables or direct color values in:
- `MainLayout.css` - Main layout colors
- `App.css` - App component colors
- Component CSS files - Button and accent colors

### Color Variables (if using CSS variables)
```css
:root {
  --green-primary: #4CAF50;
  --green-dark: #2e7d32;
  --green-darker: #1b5e20;
  --green-light: #e8f5e9;
  --green-lighter: #f0f9f4;
}
```

## Integration

1. **Import MainLayout** in your root component:
   ```jsx
   import MainLayout from './components/MainLayout';
   ```

2. **Wrap your content**:
   ```jsx
   <MainLayout user={user} onLogout={handleLogout}>
     {/* Your page content */}
   </MainLayout>
   ```

3. **Import CSS**:
   ```jsx
   import './components/MainLayout.css';
   import './components/App.css';
   ```

## Green Color Usage Summary

| Element | Color | Usage |
|---------|-------|-------|
| Edit Buttons | `#4CAF50` | Primary action buttons |
| Button Hover | `#45a049` | Hover state |
| Footer | `#2e7d32` → `#1b5e20` | Footer gradient |
| Section Border | `#4CAF50` | Left border accent |
| Top Accent | `#4CAF50` | Fixed top bar |
| Background | `#f0f9f4` → `#e8f5e9` | Page background gradient |

## Notes

- The navbar currently uses a purple gradient but can be customized to match the green theme
- All green colors follow Material Design green palette
- The layout is fully responsive and accessible
- Dark mode support is included (optional)
