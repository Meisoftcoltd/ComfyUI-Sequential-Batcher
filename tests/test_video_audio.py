import sys
import types
import pytest
from unittest.mock import MagicMock, PropertyMock, patch
import os

# Create persistent mocks that we will reset in each test
m_torch = MagicMock()
m_torchaudio = MagicMock()
m_transforms = MagicMock()

# Mock dependencies before importing anything that might depend on them
sys.modules["torch"] = m_torch
sys.modules["torchaudio"] = m_torchaudio
sys.modules["torchaudio.transforms"] = m_transforms

sys.modules["folder_paths"] = MagicMock()
sys.modules["nodes"] = MagicMock()
sys.modules["comfy"] = MagicMock()
sys.modules["comfy.utils"] = MagicMock()
sys.modules["comfy.model_management"] = MagicMock()
sys.modules["tqdm"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["numpy"] = MagicMock()

def get_extract_and_standardize_audio():
    # Read the file
    video_path = os.path.join(os.path.dirname(__file__), "..", "video.py")
    with open(video_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Mock 'from . import register_node' by replacing it
    code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")

    # ENSURE import torchaudio.transforms as T uses our mock
    # We can do this by replacing the string in the code
    code = code.replace("import torchaudio.transforms as T", "T = m_transforms")

    video_module = types.ModuleType("video")
    # We need to set some things in the module dict that might be needed
    video_module.__dict__.update({
        "__file__": video_path,
        "torch": m_torch,
        "torchaudio": m_torchaudio,
        "m_transforms": m_transforms,
        "os": os,
        "sys": sys,
        "logging": MagicMock(),
        "ThreadPoolExecutor": MagicMock(),
        "tqdm": MagicMock(),
        "comfy": sys.modules["comfy"],
        "folder_paths": sys.modules["folder_paths"],
        "nodes": sys.modules["nodes"],
        "subprocess": MagicMock(),
        "math": MagicMock(),
        "time": MagicMock(),
        "uuid": MagicMock(),
        "redirect_stdout": MagicMock(),
        "redirect_stderr": MagicMock(),
    })

    exec(code, video_module.__dict__)

    return video_module.extract_and_standardize_audio

# We will load the function ONCE at the module level to avoid re-execing video.py
# which might have side effects on sys.modules or other things.
_extract_and_standardize_audio = get_extract_and_standardize_audio()

@pytest.fixture
def func():
    # Reset mocks before each test
    m_torch.reset_mock()
    m_torchaudio.reset_mock()
    m_transforms.reset_mock()

    # Re-ensure torch.mean exists after reset as it's used in the function
    m_torch.mean = MagicMock()

    # Return the already loaded function
    return _extract_and_standardize_audio

def test_extract_and_standardize_audio_exception(func):
    # Mock torchaudio.load to raise an Exception
    m_torchaudio.load.side_effect = Exception("Test exception")

    with pytest.raises(Exception) as excinfo:
        func("dummy_path")

    assert str(excinfo.value) == "Test exception"
    m_torchaudio.load.assert_called_once_with("dummy_path")

def test_extract_and_standardize_audio_happy_path_no_resample_stereo(func):
    m_torchaudio.load.side_effect = None
    # Mock waveform: 2 channels, some length
    mock_waveform = MagicMock()
    # Use PropertyMock for shape to avoid it being a MagicMock that causes issues in comparison
    type(mock_waveform).shape = PropertyMock(return_value=(2, 1000))
    m_torchaudio.load.return_value = (mock_waveform, int(44100))

    result = func("dummy_path", target_sr=44100)

    assert result["sample_rate"] == 44100
    mock_waveform.unsqueeze.assert_called_once_with(0)
    assert result["waveform"] == mock_waveform.unsqueeze.return_value

def test_extract_and_standardize_audio_resample(func):
    m_torchaudio.load.side_effect = None
    mock_waveform = MagicMock()
    type(mock_waveform).shape = PropertyMock(return_value=(2, 1000))
    m_torchaudio.load.return_value = (mock_waveform, int(48000))

    mock_resampled_waveform = MagicMock()
    type(mock_resampled_waveform).shape = PropertyMock(return_value=(2, 918))

    mock_resampler = MagicMock()
    mock_resampler.return_value = mock_resampled_waveform
    m_transforms.Resample.return_value = mock_resampler

    result = func("dummy_path", target_sr=44100)

    m_transforms.Resample.assert_called_once_with(orig_freq=48000, new_freq=44100)
    mock_resampler.assert_called_once_with(mock_waveform)
    assert result["sample_rate"] == 44100
    assert result["waveform"] == mock_resampled_waveform.unsqueeze.return_value

def test_extract_and_standardize_audio_mono_to_stereo(func):
    m_torchaudio.load.side_effect = None
    mock_waveform = MagicMock()
    type(mock_waveform).shape = PropertyMock(return_value=(1, 1000))
    m_torchaudio.load.return_value = (mock_waveform, int(44100))

    mock_stereo_waveform = MagicMock()
    type(mock_stereo_waveform).shape = PropertyMock(return_value=(2, 1000))
    mock_waveform.repeat.return_value = mock_stereo_waveform

    result = func("dummy_path", target_sr=44100)

    mock_waveform.repeat.assert_called_once_with(2, 1)
    assert result["waveform"] == mock_stereo_waveform.unsqueeze.return_value

def test_extract_and_standardize_audio_multichannel_to_stereo(func):
    m_torchaudio.load.side_effect = None
    mock_waveform = MagicMock()
    type(mock_waveform).shape = PropertyMock(return_value=(6, 1000))
    m_torchaudio.load.return_value = (mock_waveform, int(44100))

    mock_mono = MagicMock()
    type(mock_mono).shape = PropertyMock(return_value=(1, 1000))
    m_torch.mean.return_value = mock_mono

    mock_stereo = MagicMock()
    type(mock_stereo).shape = PropertyMock(return_value=(2, 1000))
    mock_mono.repeat.return_value = mock_stereo

    result = func("dummy_path", target_sr=44100)

    m_torch.mean.assert_called_once_with(mock_waveform, dim=0, keepdim=True)
    mock_mono.repeat.assert_called_once_with(2, 1)
    assert result["waveform"] == mock_stereo.unsqueeze.return_value
