<template>
  <a-layout id="components-layout-demo-custom-trigger" style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible>
      <div class="logo">
        <h1>Butler</h1>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="inline">
        
        <a-menu-item key="1" @click="handleMenuItemClick('/about')">
          <pie-chart-outlined />
          <span>Option 1</span>
        </a-menu-item>
        
        <a-menu-item key="2" @click="handleMenuItemClick('/test')">
          <desktop-outlined />
          <span>Option 2</span>
        </a-menu-item>

        <a-menu-item key="3" @click="handleMenuItemClick('/workspaces')">
          <desktop-outlined />
          <span>Workspaces</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    
    <a-layout>
      
      <a-layout-header style="background: #fff; padding: 0">
      </a-layout-header>
      
      <a-layout-content style="margin: 1 16px">
        <a-breadcrumb style="margin: 16px 0"/>
        <div :style="{ padding: '24px', background: '#fff', minHeight: '360px' }">
          <router-view />
        </div>
      </a-layout-content>
      
      <a-layout-footer style="text-align: center">
        Lepton AI @ 2023
      </a-layout-footer>

    </a-layout>
  </a-layout>
</template>

<script >
import { PieChartOutlined, DesktopOutlined} from '@ant-design/icons-vue';
import { defineComponent, ref } from 'vue';

export default defineComponent({
  components: {
    PieChartOutlined,
    DesktopOutlined,
  },
  data() {
    return {
      collapsed: ref(false),
      selectedKeys: ref(['1']),
    };
  },
  methods: {
    handleMenuItemClick(path) {
      this.$router.push(path);
      
    }
  }
});
</script>

<style>
#components-layout-demo-custom-trigger .trigger {
    font-size: 18px;
    line-height: 64px;
    padding: 0 24px;
    cursor: pointer;
    transition: color 0.3s;
  }
  #components-layout-demo-custom-trigger .trigger:hover {
    color: #1890ff;
  }
  #components-layout-demo-custom-trigger .logo {
    height: 32px;
    margin: 16px;
  }
  #components-layout-demo-custom-trigger .logo h1 {
    color: rgba(255, 255, 255, 0.85);
  }
  #components-layout-demo-custom-trigger .ant-layout-sider-children {
    height: 100vh;
  }
</style>
