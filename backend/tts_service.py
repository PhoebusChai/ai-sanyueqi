"""GPT-SoVITS TTS 服务 (直接调用库)"""
import os
import sys
import io
import numpy as np
from pathlib import Path

# GPT-SoVITS 路径配置 (相对于项目根目录)
_BACKEND_DIR = Path(__file__).parent
_PROJECT_ROOT = _BACKEND_DIR.parent
GPT_SOVITS_PATH = os.getenv("GPT_SOVITS_PATH", str(_PROJECT_ROOT / "GPT-SoVITS"))
GPT_SOVITS_CORE_PATH = os.path.join(GPT_SOVITS_PATH, "GPT_SoVITS")

# 模型路径 (在 GPT-SoVITS 预训练模型目录)
MODEL_DIR = Path(GPT_SOVITS_CORE_PATH) / "pretrained_models"
GPT_MODEL = str(MODEL_DIR / "（GPT）March7th_med-e5.ckpt")
SOVITS_MODEL = str(MODEL_DIR / "（SoVITS）March7th_med_e2_s388_l32.pth")

# 参考音频配置 (V3 模型必须)
REF_AUDIO = str(_BACKEND_DIR / "model" / "tts" / "20251229_102109.wav")
REF_TEXT = "所有没见过的东西都要拍下来"

# 添加 GPT-SoVITS 到 Python 路径
for path in [
    GPT_SOVITS_PATH,
    GPT_SOVITS_CORE_PATH,
    os.path.join(GPT_SOVITS_CORE_PATH, "eres2net"),
]:
    if path not in sys.path:
        sys.path.insert(0, path)


class TTSService:
    def __init__(self):
        self.initialized = False
        self.tts_pipeline = None

    def _init_model(self):
        """延迟初始化模型"""
        if self.initialized:
            return

        # 切换到 GPT-SoVITS 目录 (内部用相对路径查找底模)
        original_cwd = os.getcwd()
        os.chdir(GPT_SOVITS_PATH)

        try:
            import torch
            from TTS_infer_pack.TTS import TTS, TTS_Config

            # 自动检测设备
            use_cuda = torch.cuda.is_available()
            device = "cuda" if use_cuda else "cpu"
            print(f"[TTS] CUDA available: {use_cuda}, using device: {device}")

            # V3 模型配置
            config = TTS_Config({"version": "v3"})
            config.device = device
            config.is_half = use_cuda  # 半精度只在 GPU 上使用
            config.t2s_weights_path = GPT_MODEL
            config.vits_weights_path = SOVITS_MODEL

            self.tts_pipeline = TTS(config)
            self.initialized = True
            print(f"[TTS] 模型加载成功")
            print(f"  - GPT: {GPT_MODEL}")
            print(f"  - SoVITS: {SOVITS_MODEL}")

        except ImportError as e:
            os.chdir(original_cwd)
            print(f"[TTS] 导入失败，请确认 GPT-SoVITS 路径: {GPT_SOVITS_PATH}")
            raise e
        except Exception as e:
            os.chdir(original_cwd)
            print(f"[TTS] 模型加载失败: {e}")
            raise e
        finally:
            os.chdir(original_cwd)

    def synthesize(self, text: str) -> bytes:
        """合成语音，返回 WAV 音频数据"""
        self._init_model()

        inputs = {
            "text": text,
            "text_lang": "zh",
            "text_split_method": "cut5",
            "speed_factor": 1.0,
            # V3 模型必须提供参考音频
            "ref_audio_path": REF_AUDIO,
            "prompt_text": REF_TEXT,
            "prompt_lang": "zh",
            # 关闭并行推理，避免 V3 模型卡住
            "parallel_infer": True,
        }

        result = self.tts_pipeline.run(inputs)
        sample_rate, audio_data = next(result)
        wav_bytes = self._to_wav(audio_data, sample_rate)
        return wav_bytes

    async def synthesize_async(self, text: str) -> bytes:
        """异步合成语音"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.synthesize, text)

    def _to_wav(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        """将音频数据转换为 WAV 格式"""
        import wave

        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return buffer.getvalue()


tts_service = TTSService()
