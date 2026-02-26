# Quick Fix: Display Only 3 Activities in Overview

## The Problem
The overview page shows more than 3 activities or isn't working.

## The Solution

Find the component that's actually being used at `/riggstech/admin/overview` and make these changes:

### Step 1: Find the Component
Search your codebase for:
- Files containing "recent activities" or "activities"
- Components that fetch from `/api/v1/activities`
- Files named `Overview`, `Dashboard`, or similar

### Step 2: Update the API Call
Change the API call to fetch exactly 3 items:

```jsx
// BEFORE (might be page_size=10, 20, 50, or 100)
const response = await fetch(
  'http://localhost:8000/api/v1/activities?page=1&page_size=10',
  { headers: getAuthHeaders() }
);

// AFTER (change to page_size=3)
const response = await fetch(
  'http://localhost:8000/api/v1/activities?page=1&page_size=3',
  { headers: getAuthHeaders() }
);
```

### Step 3: Limit the Results
After getting the data, limit it to exactly 3:

```jsx
// BEFORE
const data = await response.json();
setRecentActivities(data.items || []);

// AFTER
const data = await response.json();
const items = Array.isArray(data?.items) ? data.items : [];
const limitedActivities = items.slice(0, 3); // Limit to exactly 3
setRecentActivities(limitedActivities);
```

### Complete Example Function

```jsx
const loadRecentActivities = async () => {
  setLoading(true);
  setError('');
  try {
    // Fetch exactly 3 activities
    const response = await fetch(
      'http://localhost:8000/api/v1/activities?page=1&page_size=3',
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tenant-Name': localStorage.getItem('tenantName') || 'riggstech',
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to load recent activities');
    }

    const data = await response.json();
    const items = Array.isArray(data?.items) ? data.items : [];
    
    // CRITICAL: Limit to exactly 3
    const limitedActivities = items.slice(0, 3);
    setRecentActivities(limitedActivities);
  } catch (err) {
    console.error('Error loading recent activities:', err);
    setError(err.message || 'Failed to load recent activities');
  } finally {
    setLoading(false);
  }
};
```

## If You Can't Find the Component

1. **Check Browser DevTools:**
   - Open DevTools (F12)
   - Go to Network tab
   - Navigate to `/riggstech/admin/overview`
   - Look for the activities API call
   - Check which component made the call (Sources tab)

2. **Search Your Frontend Code:**
   ```bash
   # Search for activities API calls
   grep -r "activities?page" frontend/
   grep -r "recentActivities" frontend/
   grep -r "page_size" frontend/
   ```

3. **Check Router Configuration:**
   - Look for router files (App.jsx, routes.js, router.js, etc.)
   - Find the route definition for `/admin/overview`
   - See which component is mapped to that route

## Files Already Created

I've created `frontend/components/Overview.jsx` which is correctly configured. You need to:
1. Import it in your router
2. Map it to the `/riggstech/admin/overview` route
3. Or replace your existing overview component with this one

## Still Not Working?

Please provide:
1. The file path of the component actually being used
2. Any error messages from the browser console
3. The network request details (from DevTools Network tab)
