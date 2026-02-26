<template>
  <nav class="navbar">
    <div class="navbar-container">
      <!-- Logo/Brand -->
      <div class="navbar-brand">
        <router-link to="/" class="brand-link">
          <span class="brand-text">MTSMS</span>
        </router-link>
      </div>

      <!-- Desktop Menu -->
      <ul class="navbar-menu" :class="{ active: isMenuOpen }">
        <li 
          v-for="(item, index) in filteredMenuItems" 
          :key="index" 
          class="navbar-item"
        >
          <router-link 
            :to="item.path" 
            class="navbar-link" 
            @click="closeMenu"
          >
            {{ item.label }}
          </router-link>
        </li>
      </ul>

      <!-- User Menu -->
      <div class="navbar-user">
        <div v-if="user" class="user-info">
          <span class="user-name">{{ user.username || user.email }}</span>
          <span class="user-role">{{ user.role }}</span>
        </div>
        <button v-if="onLogout" class="logout-btn" @click="handleLogout">
          Logout
        </button>
      </div>

      <!-- Mobile Menu Toggle -->
      <button 
        class="navbar-toggle"
        :class="{ active: isMenuOpen }"
        @click="toggleMenu"
        aria-label="Toggle menu"
      >
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
      </button>
    </div>
  </nav>
</template>

<script>
export default {
  name: 'Navbar',
  props: {
    user: {
      type: Object,
      default: null
    },
    onLogout: {
      type: Function,
      default: null
    }
  },
  data() {
    return {
      isMenuOpen: false,
      isMobile: window.innerWidth < 768,
      menuItems: [
        { label: 'Dashboard', path: '/dashboard', roles: ['admin', 'staff', 'teacher', 'student', 'parent'] },
        { label: 'Students', path: '/students', roles: ['admin', 'staff', 'teacher'] },
        { label: 'Teachers', path: '/teachers', roles: ['admin', 'staff'] },
        { label: 'Courses', path: '/courses', roles: ['admin', 'staff', 'teacher'] },
        { label: 'Schedules', path: '/schedules', roles: ['admin', 'staff', 'teacher', 'student'] },
        { label: 'Assignments', path: '/assignments', roles: ['admin', 'staff', 'teacher', 'student'] },
        { label: 'Announcements', path: '/announcements', roles: ['admin', 'staff', 'teacher', 'student', 'parent'] },
        { label: 'Activities', path: '/activities', roles: ['admin', 'staff'] },
        { label: 'Users', path: '/users', roles: ['admin', 'super_admin'] },
        { label: 'Classes', path: '/classes', roles: ['admin', 'staff'] },
        { label: 'Enrollments', path: '/enrollments', roles: ['admin', 'staff'] },
        { label: 'Complaints', path: '/complaints', roles: ['admin', 'staff', 'student', 'parent'] },
        { label: 'System Admin', path: '/system-admin', roles: ['super_admin', 'system_admin', 'system_super_admin'] },
        { label: 'Settings', path: '/settings', roles: ['admin', 'staff'] },
      ]
    };
  },
  computed: {
    filteredMenuItems() {
      if (!this.user) return [];
      
      return this.menuItems.filter(item => 
        item.roles.some(role => 
          this.user.role === role || 
          (role === 'admin' && this.user.role?.startsWith('system_')) ||
          (role === 'super_admin' && (this.user.role === 'super_admin' || this.user.role?.startsWith('system_')))
        )
      );
    }
  },
  mounted() {
    window.addEventListener('resize', this.handleResize);
    this.handleResize();
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
    },
    closeMenu() {
      this.isMenuOpen = false;
    },
    handleResize() {
      this.isMobile = window.innerWidth < 768;
      if (!this.isMobile) {
        this.isMenuOpen = false;
      }
    },
    handleLogout() {
      if (this.onLogout) {
        this.onLogout();
      }
    }
  }
};
</script>

<style scoped>
@import './Navbar.css';
</style>
