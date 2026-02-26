<template>
  <div class="lecturer-management">
    <div class="page-header">
      <h1>Lecturer Management</h1>
      <button class="btn-primary" @click="showAddModal = true">Add New Lecturer</button>
    </div>

    <div class="table-container-wrapper">
      <div class="table-container">
        <table class="lecturer-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Employee ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Department</th>
              <th>Qualification</th>
              <th>Specialization</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9" class="loading-cell">Loading lecturers...</td>
            </tr>
            <tr v-else-if="error">
              <td colspan="9" class="error-cell">Error: {{ error }}</td>
            </tr>
            <tr v-else-if="teachers.length === 0">
              <td colspan="9" class="no-data">No lecturers found</td>
            </tr>
            <tr v-else v-for="teacher in teachers" :key="teacher.id">
              <td>{{ teacher.id }}</td>
              <td>{{ teacher.employee_id }}</td>
              <td class="name-cell">
                {{ teacher.firstname }} {{ teacher.middlename || '' }} {{ teacher.lastname }}
              </td>
              <td>{{ teacher.email }}</td>
              <td>{{ teacher.phone }}</td>
              <td>{{ teacher.department_id }}</td>
              <td class="wrap">{{ teacher.qualification || 'N/A' }}</td>
              <td class="wrap">{{ teacher.specialization || 'N/A' }}</td>
              <td class="actions-cell">
                <button class="btn-edit" @click="editTeacher(teacher)">Edit</button>
                <button class="btn-delete" @click="deleteTeacher(teacher.id)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination">
      <button 
        @click="page = Math.max(1, page - 1)" 
        :disabled="page === 1"
        class="btn-pagination"
      >
        Previous
      </button>
      <span class="page-info">
        Page {{ page }} of {{ totalPages }} ({{ total }} total)
      </span>
      <button 
        @click="page = page + 1" 
        :disabled="page >= totalPages"
        class="btn-pagination"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LecturerManagement',
  data() {
    return {
      teachers: [],
      loading: true,
      error: null,
      page: 1,
      pageSize: 10,
      total: 0,
      showAddModal: false
    };
  },
  computed: {
    totalPages() {
      return Math.ceil(this.total / this.pageSize);
    }
  },
  mounted() {
    this.fetchTeachers();
  },
  watch: {
    page() {
      this.fetchTeachers();
    },
    pageSize() {
      this.fetchTeachers();
    }
  },
  methods: {
    async fetchTeachers() {
      try {
        this.loading = true;
        this.error = null;
        
        const token = localStorage.getItem('token');
        const tenantName = localStorage.getItem('tenantName') || 'riggstech';
        
        const response = await fetch(
          `http://localhost:8000/api/v1/teachers?page=${this.page}&page_size=${this.pageSize}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'X-Tenant-Name': tenantName,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch teachers');
        }

        const data = await response.json();
        this.teachers = data.items || [];
        this.total = data.total || 0;
      } catch (err) {
        this.error = err.message;
        console.error('Error fetching teachers:', err);
      } finally {
        this.loading = false;
      }
    },
    editTeacher(teacher) {
      // Implement edit functionality
      console.log('Edit teacher:', teacher);
    },
    deleteTeacher(teacherId) {
      // Implement delete functionality
      if (confirm('Are you sure you want to delete this lecturer?')) {
        console.log('Delete teacher:', teacherId);
      }
    }
  }
};
</script>

<style scoped>
@import './LecturerManagement.css';
</style>
