<script lang="ts" setup>
defineOptions({ name: 'WalnutSlogan' });

/** 核桃外轮廓 */
const OUTLINE =
  'M120 28 C158 28 186 58 190 100 C193 138 176 176 148 196 C138 203 128 208 120 208 C112 208 102 203 92 196 C64 176 47 138 50 100 C54 58 82 28 120 28 Z';

/** 中缝 + 核仁纹路（底层常驻实线，叠层跑流光） */
const VEINS = [
  'M120 34 C116 70 124 120 120 202',
  'M112 52 C92 58 84 74 70 76',
  'M110 84 C92 90 88 106 72 110',
  'M112 118 C96 124 92 140 78 146',
  'M114 152 C102 158 98 168 90 174',
  'M128 52 C148 58 156 74 170 76',
  'M130 84 C148 90 152 106 168 110',
  'M128 118 C144 124 148 140 162 146',
  'M126 152 C138 158 142 168 150 174',
];

/** 脉络节点：[cx, cy, r] */
const NODES: [number, number, number][] = [
  [120, 28, 2.4],
  [120, 208, 2.4],
  [70, 76, 2],
  [72, 110, 2],
  [78, 146, 2],
  [90, 174, 2],
  [170, 76, 2],
  [168, 110, 2],
  [162, 146, 2],
  [150, 174, 2],
  [118, 84, 1.7],
  [122, 140, 1.7],
];

/** 星点装饰（仅暗色显示）：[left %, top %, 动画延迟 s] */
const STARS: [number, number, number][] = [
  [14, 16, 0],
  [26, 34, -1.2],
  [18, 66, -2.1],
  [30, 84, -0.6],
  [44, 10, -1.8],
  [60, 14, -3],
  [74, 20, -0.9],
  [84, 40, -2.4],
  [80, 72, -1.5],
  [64, 88, -2.8],
  [40, 90, -1.1],
  [12, 46, -1.9],
];
</script>

<template>
  <div class="walnut-slogan" aria-hidden="true">
    <i
      v-for="(star, index) in STARS"
      :key="index"
      class="star"
      :style="{
        left: `${star[0]}%`,
        top: `${star[1]}%`,
        animationDelay: `${star[2]}s`,
      }"
    ></i>
    <div class="halo"></div>
    <svg class="walnut-svg" viewBox="0 0 240 240">
      <path class="w-outline" :d="OUTLINE" />
      <!-- 底层：常驻实线纹路，静态下结构完整 -->
      <g class="w-base">
        <path v-for="(vein, index) in VEINS" :key="`b-${index}`" :d="vein" />
      </g>
      <!-- 叠层：沿纹路循环流动的光脉冲 -->
      <g class="w-pulse">
        <path
          v-for="(vein, index) in VEINS"
          :key="`p-${index}`"
          :d="vein"
          :style="{ animationDelay: `${index * 0.4}s` }"
        />
      </g>
      <g class="w-nodes">
        <circle
          v-for="(node, index) in NODES"
          :key="`n-${index}`"
          :cx="node[0]"
          :cy="node[1]"
          :r="node[2]"
        />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.walnut-slogan {
  --ws-amber: #a05c26;
  --ws-cyan: #0f7f8f;
  --ws-glow: rgba(180, 105, 46, 0.16);
  --ws-glow-c: rgba(15, 127, 143, 0.3);
  --ws-star: #f4ede2;

  position: relative;
  display: grid;
  place-items: center;
  width: min(78%, 400px);
  aspect-ratio: 1;
}

.dark .walnut-slogan {
  --ws-amber: #e8a752;
  --ws-cyan: #56d8e4;
  --ws-glow: rgba(232, 167, 82, 0.32);
  --ws-glow-c: rgba(86, 216, 228, 0.45);
}

.halo {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle, var(--ws-glow) 0%, transparent 62%);
  animation: ws-breath 5s ease-in-out infinite;
}

@keyframes ws-breath {
  0%,
  100% {
    transform: scale(0.94);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.9;
  }
}

/* 星点只在暗色出现，浅色下避免像屏幕污渍 */
.star {
  display: none;
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: var(--ws-star);
  opacity: 0.15;
  animation: ws-twinkle 4s ease-in-out infinite;
}

.dark .star {
  display: block;
}

@keyframes ws-twinkle {
  0%,
  100% {
    opacity: 0.15;
  }
  50% {
    opacity: 0.6;
  }
}

.walnut-svg {
  position: relative;
  z-index: 1;
  width: 100%;
  height: auto;
}

.walnut-svg path {
  fill: none;
  stroke-linecap: round;
}

.w-outline {
  stroke: var(--ws-amber);
  stroke-width: 2;
  opacity: 0.65;
  filter: drop-shadow(0 0 6px var(--ws-glow));
}

.w-base path {
  stroke: var(--ws-amber);
  stroke-width: 1.2;
  opacity: 0.4;
}

.w-pulse path {
  stroke: var(--ws-cyan);
  stroke-width: 1.6;
  opacity: 0.9;
  stroke-dasharray: 16 150;
  animation: ws-flow 3.6s linear infinite;
  filter: drop-shadow(0 0 4px var(--ws-glow-c));
}

@keyframes ws-flow {
  to {
    stroke-dashoffset: -166;
  }
}

.w-nodes circle {
  fill: var(--ws-cyan);
  opacity: 0.35;
  animation: ws-twinkle 2.6s ease-in-out infinite;
}

.w-nodes circle:nth-child(2n) {
  animation-delay: 0.7s;
}

.w-nodes circle:nth-child(3n) {
  animation-delay: 1.3s;
}

@media (prefers-reduced-motion: reduce) {
  .walnut-slogan *,
  .walnut-slogan *::before,
  .walnut-slogan *::after {
    animation: none !important;
  }

  /* 关闭动画时隐藏脉冲叠层，保留完整实线线稿 */
  .w-pulse {
    display: none;
  }

  .w-nodes circle {
    opacity: 0.6;
  }
}
</style>
