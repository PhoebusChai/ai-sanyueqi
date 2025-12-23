<template>
  <div class="pet-container" ref="containerRef" @mousedown="handleContainerClick">
    <!-- 左侧气泡框 -->
    <div class="speech-area" @click="hideControls">
      <div class="speech-bubble" v-show="speechText && showBubble">
        <span>{{ speechText }}</span>
      </div>
    </div>

    <!-- 中间模型区域 -->
    <div class="model-area" @mousedown="handleModelMouseDown" @contextmenu.prevent="toggleControls">
      <canvas ref="canvasRef" class="live2d-canvas"></canvas>
    </div>

    <!-- 右侧菜单 -->
    <div class="menu-area" @click.stop>
      <div class="pet-controls" v-show="showControls">
        <button class="control-btn" @click="toggleDrag" title="拖动开关">
          <component :is="isDraggable ? Move : Lock" :size="18" />
        </button>
        <button class="control-btn" @click="nextMotion" title="切换动作">
          <Play :size="18" />
        </button>
        <button class="control-btn" @click="nextExpression" title="切换表情">
          <Smile :size="18" />
        </button>
        <button class="control-btn" @click="toggleInput" title="输入框开关">
          <component :is="showInput ? EyeOff : Eye" :size="18" />
        </button>
      </div>
    </div>

    <!-- 底部消息发送（覆盖在模型上方） -->
    <div class="message-input-area" v-show="showInput" @click.stop>
      <input 
        type="text" 
        v-model="inputMessage" 
        @keyup.enter="sendMessage"
        placeholder="说点什么..."
        class="message-input"
      />
      <button class="send-btn" @click="sendMessage" :disabled="isLoading">
        <Send :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

const API_BASE = 'http://localhost:8000'

let model = null
let appWindow = null
let speechTimer = null

const speeches = [
  '你好呀！我是三月七~',
  '今天也要元气满满哦！',
  '有什么我能帮你的吗？',
  '开拓者，要一起冒险吗？',
  '记得按时休息哦~',
  '三月七永远支持你！'
]

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
    
    // 回复完成后设置自动消失
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

const toggleInput = () => {
  showInput.value = !showInput.value
}

const toggleControls = () => {
  showControls.value = !showControls.value
}

const hideControls = () => {
  showControls.value = false
}

// 左键按下拖动（仅在拖动模式下）
const handleModelMouseDown = async (e) => {
  if (e.button !== 0) return // 只响应左键
  if (appWindow && isDraggable.value) {
    await appWindow.startDragging()
  }
}

const handleContainerClick = async (e) => {
  if (e.button !== 0) return
  if (e.target.closest('.pet-controls') || e.target.closest('.control-btn')) return
  if (e.target.closest('.model-area')) return
  hideControls()
  if (appWindow && isDraggable.value) {
    await appWindow.startDragging()
  }
}

const initLive2D = async () => {
  try {
    const PIXI = await import('pixi.js')
    const { Live2DModel } = await import('pixi-live2d-display/cubism4')
    
    Live2DModel.registerTicker(PIXI.Ticker)
    
    // 使用高分辨率渲染，解决模糊问题
    const dpr = window.devicePixelRatio || 1
    const displayWidth = 320
    const displayHeight = 450
    
    const app = new PIXI.Application({
      view: canvasRef.value,
      transparent: true,
      autoStart: true,
      width: displayWidth * dpr,
      height: displayHeight * dpr,
      resolution: dpr,
      autoDensity: true
    })

    // 三月七模型
    const modelUrl = '/model/sanyueqi/march7th.model3.json'
    
    model = await Live2DModel.from(modelUrl)
    model.scale.set(0.06)
    model.anchor.set(0.5, 0.35)
    model.x = displayWidth / 2
    model.y = displayHeight / 2
    
    app.stage.addChild(model)
    
    model.on('hit', () => playMotion('tap'))
    showSpeech('你好呀！我是三月七~')
  } catch (error) {
    console.error('Live2D 加载失败:', error)
    showSpeech('模型加载中...')
  }
}

onMounted(async () => {
  try {
    const tauriWindow = await import('@tauri-apps/api/window')
    appWindow = tauriWindow.appWindow
  } catch (e) {}
  initLive2D()
})
</script>

<style scoped>
.pet-container {
  width: 100%;
  height: 100%;
  cursor: grab;
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: stretch;
}

.pet-container:active { cursor: grabbing; }

/* 左侧气泡区域 */
.speech-area {
  flex: 1;
  min-width: 110px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding-top: 80px;
  padding-right: 8px;
  flex-shrink: 0;
}

.speech-bubble {
  background: rgba(255, 182, 193, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 13px;
  max-width: 100px;
  word-wrap: break-word;
  text-align: center;
  line-height: 1.4;
  color: white;
  animation: bubbleFadeIn 0.3s ease-out;
}

@keyframes bubbleFadeIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

/* 中间模型区域 */
.model-area {
  display: flex;
  width: 220px;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.live2d-canvas {
  width: 200px;
  height: 450px;
}

/* 右侧菜单区域 */
.menu-area {
  width: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pet-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-btn {
  width: 36px;
  height: 36px;
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

/* 底部消息输入（绝对定位覆盖） */
.message-input-area {
  position: absolute;
  bottom: 15px;
  right: 12px;
  display: flex;
  gap: 8px;
}

.message-input {
  width: 300px;
  margin-left: 40px;
  padding: 11px 14px;
  border: none;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  outline: none;
  color: #4a5568;
}

.message-input::placeholder {
  color: #a0aec0;
}

.send-btn {
  width: 36px;
  height: 36px;
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
