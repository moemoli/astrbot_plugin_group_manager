<script setup lang="ts">
import { computed } from 'vue'
import type { TabsPaneContext } from 'element-plus'
import { RouterView, useRoute, useRouter } from 'vue-router'

interface AppNavItem {
  label: string
  path: string
}

const route = useRoute()
const router = useRouter()

const navItems: AppNavItem[] = [
  { label: '群管理', path: '/' },
  { label: '关于', path: '/about' },
]

const activePath = computed(() => route.path)

async function navigate(path: string) {
  if (route.path === path) {
    return
  }
  await router.push(path)
}

function onMenuSelect(index: string) {
  void navigate(index)
}

function onTabClick(pane: TabsPaneContext) {
  void navigate(String(pane.paneName ?? ''))
}
</script>

<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="layout-aside">
      <div class="app-title">Group Manager</div>
      <el-menu
        :default-active="activePath"
        class="side-menu"
        @select="onMenuSelect"
      >
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          {{ item.label }}
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <el-tabs
          :model-value="activePath"
          type="card"
          class="route-tabs"
          @tab-click="onTabClick"
        >
          <el-tab-pane
            v-for="item in navItems"
            :key="item.path"
            :label="item.label"
            :name="item.path"
          />
        </el-tabs>
      </el-header>

      <el-main class="layout-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  height: 100vh;
}

.layout-aside {
  border-right: none;
  background: linear-gradient(180deg, #fafbfc 0%, #f0f2f5 100%);
  overflow: hidden;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.04);
  z-index: 10;
}

.app-title {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: -0.3px;
  color: #1a1a2e;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.side-menu {
  border-right: none;
  --el-menu-active-color: #4f6ef7;
}

.side-menu .el-menu-item {
  margin: 4px 8px;
  border-radius: 8px;
  height: 40px;
  line-height: 40px;
  transition: all 0.2s ease;
}

.side-menu .el-menu-item:hover {
  background: rgba(79, 110, 247, 0.08);
}

.side-menu .el-menu-item.is-active {
  background: rgba(79, 110, 247, 0.12);
  color: #4f6ef7;
  font-weight: 600;
}

.layout-header {
  height: 52px;
  padding: 6px 20px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
}

.route-tabs {
  width: 100%;
}

.layout-main {
  padding: 20px 24px;
  background: #f5f7fa;
  overflow: auto;
}
</style>
