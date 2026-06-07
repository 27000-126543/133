<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <div class="error-code">404</div>
      <h1 class="error-title">页面未找到</h1>
      <p class="error-description">抱歉，您访问的页面不存在或已被移除。</p>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">
          <el-icon><HomeFilled /></el-icon>返回首页
        </el-button>
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>返回上一页
        </el-button>
      </div>
      <div class="error-illustration">
        <el-icon :size="120" color="#667eea"><WarningFilled /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { HomeFilled, ArrowLeft, WarningFilled } from '@element-plus/icons-vue'

const router = useRouter()

function goHome() {
  router.push('/')
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.not-found-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.not-found-container::before {
  content: '';
  position: absolute;
  width: 500px;
  height: 500px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  top: -200px;
  right: -200px;
}

.not-found-container::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  bottom: -100px;
  left: -100px;
}

.not-found-content {
  text-align: center;
  color: white;
  z-index: 1;
  position: relative;
}

.error-code {
  font-size: 180px;
  font-weight: bold;
  line-height: 1;
  text-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.error-title {
  font-size: 36px;
  margin: 20px 0 10px 0;
}

.error-description {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 40px;
}

.error-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 60px;
}

.error-actions .el-button {
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 30px;
}

.error-illustration {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
}
</style>
