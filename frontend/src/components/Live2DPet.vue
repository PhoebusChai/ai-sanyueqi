<template>
  <div class="pet-container" ref="containerRef" @mousedown="handleContainerClick">
    <!-- 气泡框 - 左上角 -->
    <div class="speech-bubble" v-show="speechText && showBubble" @click="hideControls">
      <span>{{ speechText }}</span>
    </div>

    <!-- Live2D 模型 - 居中 -->
    <canvas ref="canvasRef" class="live2d-canvas" 
      @mousedown="handleModelMouseDown" 
      @contextmenu.prevent="toggleControls">
    </canvas>

    <!-- 右侧菜单 -->
    <div class="pet-controls" v-show="showControls" @click.stop>
      <button class="control-btn" @click="toggleDrag" title="拖动开关">
        <component :is="isDraggable ? Move : Lock" :size="iconSize" />
      </button>
      <button class="control-btn" @click="nextMotion" title="切换动作">
        <Play :size="iconSize" />
      </button>
      <button class="control-btn" @click="nextExpression" title="切换表情">
        <Smile :size="iconSize" />
      </button>
      <button class="control-btn" @click="toggleInput" title="输入框开关">
        <component :is="showInput ? EyeOff : Eye" :size="iconSize" />
      </button>
    </div>

    <!-- 底部消息发送 -->
    <div class="message-input-area" v-show="showInput" @click.stop>
      <input 
        type="text" 
        v-model="inputMessage" 
        @keyup.enter="sendMessage"
        placeholder="说点什么..."
        class="message-input"
      />
      <button class="send-btn" @click="sendMessage" :disabled="isLoading">
        <Send :size="iconSize - 2" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Move, Lock, Play, Smile, Eye, EyeOff, Send } from 'lucide-vue-next'

const containerRef = ref(null)
const canvasRef = ref(null)
const showControls = ref(false)
const isDraggable = ref(true)
const showBubble = ref(true)
const showInput = ref(true)
const speechText = ref('')
const inputMessage = ref('')
const isLoading = ref(false)
const currentMotionIndex = ref(0)
const currentExpressionIndex = ref(0)
const scaleFactor = ref(1)

// 响应式图标大小
const iconSize = computed(() => Math.max(14, Math.floor(18 * scaleFactor.value)))

const API_BASE = 'http://localhost:8001'

let model = null
let appWindow = null
let speechTimer = null
let pixiApp = null

const showSpeech = (text, duration = 3000) => {
  if (speechTimer) clearTimeout(speechTimer)
  speechText.value = text
  if (duration > 0) {
    speechTimer = setTimeout(() => { speechText.value = '' }, duration)
  }
}

// 流式发送消息
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || isLoading.value) return
  
  inputMessage.value = ''
  isLoading.value = true
  showSpeech('思考中...', 0)
  
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    })
    
    if (!response.ok) throw new Error('请求失败')
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullReply = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            playMotion('tap')
          } else if (data.startsWith('[ERROR]')) {
            showSpeech('出错了呢...')
          } else {
            fullReply += data
            showSpeech(fullReply, 0)
          }
        }
      }
    }
    
    if (fullReply) {
      speechTimer = setTimeout(() => { speechText.value = '' }, 5000)
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    showSpeech('网络出问题了~')
  } finally {
    isLoading.value = false
  }
}

const motionGroups = ['Idle', 'Tap', 'Zhaiyan', 'Wulian', 'Star', 'Blush', 'Cry', 'Nod', 'Smile', 'Shake', 'Biye']
const expressions = ['exp1', 'exp2', 'exp3', 'exp5', 'exp6', 'exp7', 'exp8', 'exp9']

const playMotion = () => {
  if (model) {
    const motion = motionGroups[Math.floor(Math.random() * motionGroups.length)]
    model.motion(motion)
  }
}

const nextMotion = () => {
  if (model) {
    currentMotionIndex.value = (currentMotionIndex.value + 1) % motionGroups.length
    const motion = motionGroups[currentMotionIndex.value]
    model.motion(motion)
    showSpeech(`动作: ${motion}`)
  }
}

const nextExpression = () => {
  if (model) {
    currentExpressionIndex.value = (currentExpressionIndex.value + 1) % expressions.length
    const exp = expressions[currentExpressionIndex.value]
    model.expression(exp)
    showSpeech(`表情: ${exp}`)
  }
}

const toggleDrag = () => {
  isDraggable.value = !isDraggable.value
  showSpeech(isDraggable.value ? '可以拖动啦~' : '固定位置了~')
}

const toggleInput = () => { showInput.value = !showInput.value }
const toggleControls = () => { showControls.value = !showControls.value }
const hideControls = () => { showControls.value = false }

const handleModelMouseDown = async (e) => {
  if (e.button !== 0) return
  if (appWindow && isDraggable.value) {
    await appWindow.startDragging()
  }
}

const handleContainerClick = async (e) => {
  if (e.button !== 0) return
  if (e.target.closest('.pet-controls') || e.target.closest('.control-btn')) return
  if (e.target.closest('.live2d-canvas')) return
  hideControls()
  if (appWindow && isDraggable.value) {
    await appWindow.startDragging()
  }
}

// 计算缩放因子
const updateScaleFactor = () => {
  const container = containerRef.value
  if (!container) return
  
  const baseWidth = 500
  const baseHeight = 540
  const scaleX = container.clientWidth / baseWidth
  const scaleY = container.clientHeight / baseHeight
  scaleFactor.value = Math.min(scaleX, scaleY, 1.5) // 限制最大缩放
}

const initLive2D = async () => {
  try {
    const PIXI = await import('pixi.js')
    const { Live2DModel } = await import('pixi-live2d-display/cubism4')
    
    Live2DModel.registerTicker(PIXI.Ticker)
    
    const container = containerRef.value
    const canvas = canvasRef.value
    if (!container || !canvas) return
    
    updateScaleFactor()
    
    const dpr = window.devicePixelRatio || 1
    const canvasWidth = container.clientWidth
    const canvasHeight = container.clientHeight
    
    pixiApp = new PIXI.Application({
      view: canvas,
      transparent: true,
      autoStart: true,
      width: canvasWidth * dpr,
      height: canvasHeight * dpr,
      resolution: dpr,
      autoDensity: true
    })

    const modelUrl = '/model/sanyueqi/march7th.model3.json'
    
    model = await Live2DModel.from(modelUrl)
    
    // 根据窗口大小计算模型缩放
    const modelScale = 0.06 * scaleFactor.value
    model.scale.set(modelScale)
    model.anchor.set(0.5, 0.5)
    model.x = canvasWidth / 2
    model.y = canvasHeight / 2
    
    pixiApp.stage.addChild(model)
    
    model.on('hit', () => playMotion('tap'))
    showSpeech('你好呀！我是三月七~')
    
    window.addEventListener('resize', handleResize)
  } catch (error) {
    console.error('Live2D 加载失败:', error)
    showSpeech('模型加载中...')
  }
}

const handleResize = () => {
  if (!pixiApp || !model || !containerRef.value) return
  
  updateScaleFactor()
  
  const dpr = window.devicePixelRatio || 1
  const canvasWidth = containerRef.value.clientWidth
  const canvasHeight = containerRef.value.clientHeight
  
  pixiApp.renderer.resize(canvasWidth * dpr, canvasHeight * dpr)
  
  const modelScale = 0.06 * scaleFactor.value
  model.scale.set(modelScale)
  model.x = canvasWidth / 2
  model.y = canvasHeight / 2
}

onMounted(async () => {
  try {
    const tauriWindow = await import('@tauri-apps/api/window')
    appWindow = tauriWindow.appWindow
  } catch (e) {}
  initLive2D()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.pet-container {
  width: 100vw;
  height: 100vh;
  cursor: grab;
  position: relative;
  overflow: hidden;
}

.pet-container:active { cursor: grabbing; }

/* Live2D Canvas - 全屏居中 */
.live2d-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* 气泡框 - 左上角 */
.speech-bubble {
  position: absolute;
  top: 12%;
  left: 8%;
  background: rgba(255, 182, 193, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 10px 14px;
  border-radius: 16px;
  font-size: clamp(11px, 2.5vw, 14px);
  max-width: min(120px, 30vw);
  word-wrap: break-word;
  text-align: center;
  line-height: 1.4;
  color: white;
  z-index: 10;
  animation: bubbleFadeIn 0.3s ease-out;
}

@keyframes bubbleFadeIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

/* 右侧控制按钮 */
.pet-controls {
  position: absolute;
  right: 8%;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: clamp(8px, 2vh, 12px);
  z-index: 10;
}

.control-btn {
  width: clamp(32px, 8vw, 40px);
  height: clamp(32px, 8vw, 40px);
  border: none;
  background: rgba(255, 182, 193, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.control-btn:hover { 
  transform: scale(1.1);
}

/* 底部消息输入 */
.message-input-area {
  position: absolute;
  bottom: 4%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  width: 80%;
  max-width: 350px;
  z-index: 10;
}

.message-input {
  flex: 1;
  padding: clamp(8px, 2vw, 12px) clamp(12px, 3vw, 16px);
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.85);
  font-size: clamp(11px, 2.5vw, 13px);
  outline: none;
  color: #4a5568;
}

.message-input::placeholder {
  color: #a0aec0;
}

.send-btn {
  width: clamp(32px, 8vw, 40px);
  height: clamp(32px, 8vw, 40px);
  flex-shrink: 0;
  border: none;
  background: rgba(255, 182, 193, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.send-btn:hover {
  transform: scale(1.1);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
