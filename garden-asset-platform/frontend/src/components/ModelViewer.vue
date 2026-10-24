<template>
  <div ref="container" class="model-viewer">
    <canvas ref="canvas" class="model-canvas"></canvas>
    <div v-if="!ready && !failed" class="model-status">正在解析三维模型…</div>
    <div v-if="failed" class="model-status is-error">模型解析失败，可下载后查看</div>
    <div v-if="ready" class="model-hint">拖拽旋转 · 滚轮缩放</div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  format: { type: String, default: '' }
})
const emit = defineEmits(['error'])

const container = ref(null)
const canvas = ref(null)
const ready = ref(false)
const failed = ref(false)

let renderer = null
let scene = null
let camera = null
let controls = null
let observer = null
let frame = null
let destroyed = false

const MODEL_FORMATS = ['glb', 'gltf', 'stl', 'obj']

function disposeObject(root) {
  root.traverse(child => {
    if (child.geometry) child.geometry.dispose()
    const materials = Array.isArray(child.material)
      ? child.material
      : child.material
        ? [child.material]
        : []
    materials.forEach(material => {
      Object.values(material).forEach(value => {
        if (value && value.isTexture) value.dispose()
      })
      material.dispose()
    })
  })
}

async function loadObject(THREE, format) {
  if (format === 'glb' || format === 'gltf') {
    const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js')
    const gltf = await new GLTFLoader().loadAsync(props.src)
    return gltf.scene
  }
  if (format === 'stl') {
    const { STLLoader } = await import('three/addons/loaders/STLLoader.js')
    const geometry = await new STLLoader().loadAsync(props.src)
    geometry.computeVertexNormals()
    return new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({ color: 0x5f7f6c, roughness: 0.55, metalness: 0.08 })
    )
  }
  if (format === 'obj') {
    const { OBJLoader } = await import('three/addons/loaders/OBJLoader.js')
    const group = await new OBJLoader().loadAsync(props.src)
    group.traverse(child => {
      if (child.isMesh) {
        child.material = new THREE.MeshStandardMaterial({
          color: 0x8a7a63,
          roughness: 0.7,
          metalness: 0.05
        })
      }
    })
    return group
  }
  throw new Error(`暂不支持 .${format} 格式的在线预览`)
}

function fitCamera(THREE, object) {
  const box = new THREE.Box3().setFromObject(object)
  if (box.isEmpty()) throw new Error('模型没有可显示的几何体')
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  object.position.sub(center)

  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = (camera.fov * Math.PI) / 180
  const distance = (maxDim / 2 / Math.tan(fov / 2)) * 1.9
  camera.position.set(distance * 0.7, distance * 0.55, distance * 0.7)
  camera.near = Math.max(distance / 1000, 0.01)
  camera.far = distance * 100
  camera.updateProjectionMatrix()
  controls.target.set(0, 0, 0)
  controls.update()
}

async function initViewer() {
  const format = (props.format || '').toLowerCase()
  if (!MODEL_FORMATS.includes(format)) {
    failed.value = true
    emit('error')
    return
  }
  try {
    const THREE = await import('three')
    const { OrbitControls } = await import('three/addons/controls/OrbitControls.js')
    if (destroyed) return

    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(45, 1, 0.01, 10000)

    renderer = new THREE.WebGLRenderer({
      canvas: canvas.value,
      antialias: true,
      alpha: true
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05

    scene.add(new THREE.HemisphereLight(0xffffff, 0x7d8c82, 2.4))
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2)
    keyLight.position.set(6, 10, 8)
    scene.add(keyLight)
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.8)
    fillLight.position.set(-6, 4, -6)
    scene.add(fillLight)

    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.autoRotate = true
    controls.autoRotateSpeed = 1.1
    controls.minDistance = 0.1

    const object = await loadObject(THREE, format)
    if (destroyed) {
      disposeObject(object)
      return
    }
    scene.add(object)
    fitCamera(THREE, object)

    observer = new ResizeObserver(() => resize())
    observer.observe(container.value)
    resize()

    const animate = () => {
      frame = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()
    ready.value = true
  } catch (error) {
    if (destroyed) return
    failed.value = true
    emit('error', error)
  }
}

function resize() {
  if (!renderer || !camera || !container.value) return
  const width = container.value.clientWidth
  const height = container.value.clientHeight
  if (!width || !height) return
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

onMounted(initViewer)

onBeforeUnmount(() => {
  destroyed = true
  if (frame) cancelAnimationFrame(frame)
  if (observer) observer.disconnect()
  if (controls) controls.dispose()
  if (scene) disposeObject(scene)
  if (renderer) {
    renderer.dispose()
    renderer = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.model-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 320px;
  overflow: hidden;
  cursor: grab;
  background:
    radial-gradient(circle at 32% 28%, rgba(255, 255, 255, 0.85), transparent 55%),
    linear-gradient(145deg, rgba(238, 242, 235, 0.9), rgba(219, 228, 219, 0.75));

  &:active {
    cursor: grabbing;
  }
}

.model-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.model-status {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: $text-secondary;
  pointer-events: none;

  &.is-error {
    color: $error-color;
  }
}

.model-hint {
  position: absolute;
  right: 14px;
  bottom: 12px;
  padding: 4px 10px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: $text-secondary;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid $border-color;
  border-radius: 999px;
  pointer-events: none;
}
</style>
