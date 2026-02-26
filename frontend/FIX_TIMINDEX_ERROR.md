# Fixing `timeIndex` Unused Variable Error

## Problem
TypeScript/ESLint error: `'timeIndex' is declared but its value is never read`

This error occurs when you have a parameter in a function (like `.map()` or `.forEach()`) that you're not using.

## Solutions

### Option 1: Use the Parameter
If you need the index, use it:

```jsx
// ✅ Good - Using timeIndex
const timeSlots = ['08:00', '09:00', '10:00'];
const slotsWithIds = timeSlots.map((time, timeIndex) => ({
  id: `slot-${timeIndex}`,
  value: time,
  label: time
}));
```

### Option 2: Prefix with Underscore (Recommended for Unused Parameters)
If you don't need the index, prefix it with `_` to indicate it's intentionally unused:

```jsx
// ✅ Good - Prefix with _ to indicate intentionally unused
const schedules = data.map((schedule, _scheduleIndex) => (
  <tr key={schedule.id}>
    <td>{schedule.id}</td>
  </tr>
));

// ✅ Also works with timeIndex
const timeSlots = ['08:00', '09:00'].map((time, _timeIndex) => (
  <option key={time} value={time}>{time}</option>
));
```

### Option 3: Remove the Parameter
If you truly don't need it, just don't include it:

```jsx
// ✅ Good - No index parameter needed
const timeSlots = ['08:00', '09:00'].map((time) => (
  <option key={time} value={time}>{time}</option>
));
```

### Option 4: Use Array Index in Key (Common Pattern)
If you need the index for React keys but don't use it elsewhere:

```jsx
// ✅ Good - Using index for key
const schedules = data.map((schedule, index) => (
  <tr key={schedule.id || index}>
    <td>{schedule.id}</td>
  </tr>
));
```

## Common Scenarios

### Scenario 1: Map with Index Not Used
```jsx
// ❌ Bad - timeIndex declared but not used
const options = timeSlots.map((time, timeIndex) => (
  <option value={time}>{time}</option>
));

// ✅ Fixed - Remove unused parameter
const options = timeSlots.map((time) => (
  <option key={time} value={time}>{time}</option>
));

// ✅ Or use it for key
const options = timeSlots.map((time, timeIndex) => (
  <option key={timeIndex} value={time}>{time}</option>
));
```

### Scenario 2: ForEach with Index Not Used
```jsx
// ❌ Bad
schedules.forEach((schedule, timeIndex) => {
  console.log(schedule);
});

// ✅ Fixed - Prefix with _
schedules.forEach((schedule, _timeIndex) => {
  console.log(schedule);
});

// ✅ Or remove it
schedules.forEach((schedule) => {
  console.log(schedule);
});
```

### Scenario 3: Filter/Reduce with Index
```jsx
// ❌ Bad
const filtered = items.filter((item, timeIndex) => item.active);

// ✅ Fixed
const filtered = items.filter((item) => item.active);

// Or if you need the index
const filtered = items.filter((item, timeIndex) => {
  return item.active && timeIndex > 0;
});
```

## ESLint Configuration (Optional)

If you want to allow unused parameters prefixed with `_`, you can configure ESLint:

```json
{
  "rules": {
    "no-unused-vars": [
      "error",
      {
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_"
      }
    ]
  }
}
```

## Quick Fix in Your Code

If you have this error in your schedule management component, find the line with `timeIndex` and either:

1. **Use it**: `const items = array.map((item, timeIndex) => ({ id: timeIndex, ...item }))`
2. **Prefix with _**: `const items = array.map((item, _timeIndex) => ...)`
3. **Remove it**: `const items = array.map((item) => ...)`

## Example Fix

```jsx
// Before (Error)
const renderTimeSlots = () => {
  return timeSlots.map((time, timeIndex) => (
    <option value={time}>{time}</option>
  ));
};

// After (Fixed - Option 1: Use it)
const renderTimeSlots = () => {
  return timeSlots.map((time, timeIndex) => (
    <option key={timeIndex} value={time}>{time}</option>
  ));
};

// After (Fixed - Option 2: Prefix with _)
const renderTimeSlots = () => {
  return timeSlots.map((time, _timeIndex) => (
    <option key={time} value={time}>{time}</option>
  ));
};

// After (Fixed - Option 3: Remove it)
const renderTimeSlots = () => {
  return timeSlots.map((time) => (
    <option key={time} value={time}>{time}</option>
  ));
};
```
