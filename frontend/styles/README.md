# Tables and Forms Overflow Styles

This directory contains CSS files to add `overflow: auto` to all tables and forms for responsive scrolling.

## Files

1. **`tables-forms.css`** - Comprehensive styles for tables and forms with detailed overflow handling
2. **`global.css`** - Global styles that apply overflow to all tables and forms automatically

## Usage

### Option 1: Import in your main CSS file
```css
@import './styles/tables-forms.css';
/* or */
@import './styles/global.css';
```

### Option 2: Link in HTML
```html
<link rel="stylesheet" href="styles/tables-forms.css">
<!-- or -->
<link rel="stylesheet" href="styles/global.css">
```

### Option 3: Import in React/Vue
```jsx
// React
import './styles/tables-forms.css';

// Vue
<style>
@import './styles/tables-forms.css';
</style>
```

## Features

✅ **Automatic Overflow**: All tables and forms get `overflow: auto` automatically
✅ **Responsive**: Works on all screen sizes
✅ **Custom Scrollbars**: Styled scrollbars for better UX
✅ **Sticky Headers**: Table headers stay visible when scrolling
✅ **Mobile Optimized**: Touch-friendly scrolling on mobile devices
✅ **Accessibility**: Proper focus states and reduced motion support

## Classes Available

### Table Classes
- `.table-wrapper` - Wrapper for tables with overflow
- `.table-container` - Container with max-height and overflow
- `.responsive-table` - Fully responsive table
- `.data-table` - Data table with overflow
- `.table-scroll` - Utility class for scrollable tables

### Form Classes
- `.form-container` - Form container with overflow
- `.form-wrapper` - Form wrapper with overflow
- `.form-scroll` - Utility class for scrollable forms
- `.modal-form` - Forms in modals with overflow
- `.inline-form` - Inline forms with proper overflow

### Utility Classes
- `.overflow-auto` - Apply overflow: auto
- `.overflow-x-auto` - Horizontal scrolling
- `.overflow-y-auto` - Vertical scrolling

## Examples

### Basic Table
```html
<div class="table-wrapper">
  <table>
    <thead>
      <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Role</th>
      </tr>
    </thead>
    <tbody>
      <!-- table rows -->
    </tbody>
  </table>
</div>
```

### Basic Form
```html
<div class="form-container">
  <form>
    <!-- form fields -->
  </form>
</div>
```

### Table with Max Height
```html
<div class="table-container">
  <table>
    <!-- table content -->
  </table>
</div>
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Notes

- Tables automatically get horizontal scrolling on small screens
- Forms get vertical scrolling when content exceeds viewport
- Scrollbars are styled for better appearance
- All styles are responsive and mobile-friendly
