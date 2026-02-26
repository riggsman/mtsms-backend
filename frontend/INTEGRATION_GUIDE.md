# Table Display Fix - Integration Guide

## Problem
Tables not displaying properly at `/admin/lecturer-management` or other table views.

## Solution
Import the table fix CSS files to ensure all tables display correctly.

## Quick Fix (Recommended)

Add this to your main CSS file or HTML head:

```html
<!-- Add this to your index.html or main layout -->
<link rel="stylesheet" href="styles/overflow-fix.css">
<link rel="stylesheet" href="styles/table-fix.css">
<link rel="stylesheet" href="styles/global.css">
```

Or in your main CSS:
```css
@import './styles/overflow-fix.css';
@import './styles/table-fix.css';
@import './styles/global.css';
```

**Important**: Import `overflow-fix.css` first to prevent page-level overflow issues.

## For Lecturer Management Specifically

1. **Copy the component**:
   - `LecturerManagement.jsx` (React)
   - `LecturerManagement.vue` (Vue)
   - `LecturerManagement.css` (Styles)

2. **Import the CSS**:
   ```jsx
   // React
   import '../styles/overflow-fix.css';
   import './LecturerManagement.css';
   import '../styles/table-fix.css';
   ```

   ```vue
   <!-- Vue -->
   <style>
   @import '../styles/overflow-fix.css';
   @import './LecturerManagement.css';
   @import '../styles/table-fix.css';
   </style>
   ```

3. **Use the component**:
   ```jsx
   // React
   import LecturerManagement from './components/LecturerManagement';
   
   function App() {
     return <LecturerManagement />;
   }
   ```

## Key CSS Rules Applied

1. **Table Display Fix**:
   ```css
   table {
     display: table !important;
   }
   ```

2. **Table Container**:
   ```css
   .table-container {
     overflow-x: auto;
     overflow-y: auto;
     max-height: 80vh;
   }
   ```

3. **Sticky Headers**:
   ```css
   table thead {
     position: sticky;
     top: 0;
   }
   ```

## API Endpoint

The component uses:
- **GET** `/api/v1/teachers?page=1&page_size=10`
- Requires: `Authorization: Bearer <token>`
- Requires: `X-Tenant-Name: <tenant_name>`

## Testing

1. Navigate to `http://localhost:5173/riggstech/admin/lecturer-management`
2. Table should display with:
   - All columns visible
   - Horizontal scrolling if needed
   - Vertical scrolling if many rows
   - Sticky header when scrolling
   - Proper cell alignment

## Troubleshooting

If table still doesn't display:

1. **Check CSS is loaded**:
   - Open browser DevTools
   - Check if `table-fix.css` is loaded
   - Verify no CSS conflicts

2. **Check table structure**:
   - Ensure `<table>`, `<thead>`, `<tbody>` tags are present
   - Verify table is inside `.table-container`

3. **Check API response**:
   - Verify API returns data
   - Check network tab for errors
   - Verify token and tenant header

4. **Force table display**:
   ```css
   table {
     display: table !important;
     visibility: visible !important;
   }
   ```

## Files to Import

**Minimum required**:
- `styles/overflow-fix.css` - Prevents page-level overflow (import first!)
- `styles/table-fix.css` - Core table fixes

**Recommended**:
- `styles/overflow-fix.css` - Prevents all overflow issues (import first!)
- `styles/table-fix.css` - Core table fixes
- `styles/global.css` - Global table/form styles
- `components/LecturerManagement.css` - Component-specific styles

## Overflow Fixes Applied

✅ **Page-level overflow prevention** - No horizontal scrolling on the page
✅ **Table container overflow** - Tables scroll within their container
✅ **Cell content overflow** - Text wraps properly in cells
✅ **Responsive overflow** - Works on all screen sizes
✅ **Box-sizing fix** - All elements use border-box
