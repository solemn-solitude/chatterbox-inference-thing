"""Acoustic feature extraction for emotional anchor validation.

This module extracts prosodic features from audio files to validate that generated
emotional anchors exhibit the expected acoustic characteristics.
"""

import logging
import numpy as np
import wave
from pathlib import Path
from typing import Dict, Any, Tuple
import warnings

logger = logging.getLogger(__name__)

# Suppress warnings from audio processing libraries
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class AcousticFeatureExtractor:
    """Extracts prosodic features from audio for emotional validation."""
    
    def __init__(self):
        """Initialize feature extractor."""
        self.sample_rate = None
        
    def load_audio(self, filepath: Path) -> Tuple[np.ndarray, int]:
        """Load audio file and return audio array and sample rate.
        
        Args:
            filepath: Path to WAV file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        try:
            with wave.open(str(filepath), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                
                # Read audio data
                audio_bytes = wav_file.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                elif sample_width == 4:
                    dtype = np.int32
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")
                
                audio_array = np.frombuffer(audio_bytes, dtype=dtype)
                
                # Convert to float32 normalized to [-1, 1]
                if dtype == np.uint8:
                    audio_array = (audio_array.astype(np.float32) - 128) / 128.0
                else:
                    audio_array = audio_array.astype(np.float32) / np.iinfo(dtype).max
                
                # Handle stereo - convert to mono if needed
                if n_channels > 1:
                    audio_array = audio_array.reshape(-1, n_channels).mean(axis=1)
                
                return audio_array, sample_rate
                
        except Exception as e:
            logger.error(f"Error loading audio file {filepath}: {e}")
            raise
    
    def extract_pitch_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract pitch (F0) features using CREPE or PyWorld.
        
        Args:
            audio: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Dictionary with pitch features
        """
        try:
            import crepe
            
            # Use CREPE for high-quality pitch extraction
            time, frequency, confidence, activation = crepe.predict(
                audio,
                sample_rate,
                viterbi=True,
                step_size=10  # 10ms hop
            )
            
            # Filter out low-confidence and zero values
            valid_mask = (confidence > 0.5) & (frequency > 50) & (frequency < 500)
            valid_frequency = frequency[valid_mask]
            
            if len(valid_frequency) == 0:
                logger.warning("No valid pitch detected")
                return {
                    'mean_pitch': 0.0,
                    'pitch_variance': 0.0,
                    'pitch_range': 0.0,
                    'pitch_std': 0.0
                }
            
            return {
                'mean_pitch': float(np.mean(valid_frequency)),
                'pitch_variance': float(np.var(valid_frequency)),
                'pitch_range': float(np.max(valid_frequency) - np.min(valid_frequency)),
                'pitch_std': float(np.std(valid_frequency))
            }
            
        except ImportError:
            logger.warning("CREPE not available, falling back to simpler pitch estimation")
            # Fallback: use autocorrelation-based pitch estimation
            return self._extract_pitch_simple(audio, sample_rate)
        except Exception as e:
            logger.error(f"Error extracting pitch features: {e}")
            return {
                'mean_pitch': 0.0,
                'pitch_variance': 0.0,
                'pitch_range': 0.0,
                'pitch_std': 0.0
            }
    
    def _extract_pitch_simple(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Simple autocorrelation-based pitch estimation (fallback).
        
        Args:
            audio: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Dictionary with pitch features
        """
        # Frame-based pitch estimation
        frame_length = int(0.03 * sample_rate)  # 30ms frames
        hop_length = int(0.01 * sample_rate)    # 10ms hop
        
        pitches = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i+frame_length]
            
            # Autocorrelation
            autocorr = np.correlate(frame, frame, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find first peak after zero lag
            min_period = int(sample_rate / 500)  # Max 500 Hz
            max_period = int(sample_rate / 50)   # Min 50 Hz
            
            if len(autocorr) > max_period:
                peak_idx = np.argmax(autocorr[min_period:max_period]) + min_period
                if autocorr[peak_idx] > 0.3 * autocorr[0]:  # Threshold
                    pitch = sample_rate / peak_idx
                    if 50 < pitch < 500:
                        pitches.append(pitch)
        
        if len(pitches) == 0:
            return {
                'mean_pitch': 0.0,
                'pitch_variance': 0.0,
                'pitch_range': 0.0,
                'pitch_std': 0.0
            }
        
        pitches = np.array(pitches)
        return {
            'mean_pitch': float(np.mean(pitches)),
            'pitch_variance': float(np.var(pitches)),
            'pitch_range': float(np.max(pitches) - np.min(pitches)),
            'pitch_std': float(np.std(pitches))
        }
    
    def extract_energy_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract energy features (RMS, dynamic range).
        
        Args:
            audio: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Dictionary with energy features
        """
        # Frame-based RMS energy
        frame_length = int(0.03 * sample_rate)  # 30ms frames
        hop_length = int(0.01 * sample_rate)    # 10ms hop
        
        rms_values = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i+frame_length]
            rms = np.sqrt(np.mean(frame**2))
            rms_values.append(rms)
        
        rms_values = np.array(rms_values)
        
        # Filter out silence
        threshold = np.percentile(rms_values, 10)
        voiced_rms = rms_values[rms_values > threshold]
        
        if len(voiced_rms) == 0:
            return {
                'mean_energy': 0.0,
                'energy_variance': 0.0,
                'energy_range': 0.0,
                'dynamic_range_db': 0.0
            }
        
        # Convert to dB
        rms_db = 20 * np.log10(voiced_rms + 1e-8)
        
        return {
            'mean_energy': float(np.mean(voiced_rms)),
            'energy_variance': float(np.var(voiced_rms)),
            'energy_range': float(np.max(voiced_rms) - np.min(voiced_rms)),
            'dynamic_range_db': float(np.max(rms_db) - np.min(rms_db))
        }
    
    def extract_temporal_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract temporal features (speaking rate, pauses).
        
        Args:
            audio: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Dictionary with temporal features
        """
        # Simple energy-based voice activity detection
        frame_length = int(0.03 * sample_rate)
        hop_length = int(0.01 * sample_rate)
        
        rms_values = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i+frame_length]
            rms = np.sqrt(np.mean(frame**2))
            rms_values.append(rms)
        
        rms_values = np.array(rms_values)
        
        # Threshold for voice activity
        threshold = np.percentile(rms_values, 30)
        is_voiced = rms_values > threshold
        
        # Count voiced segments
        voiced_changes = np.diff(is_voiced.astype(int))
        n_voiced_segments = np.sum(voiced_changes == 1)
        
        # Estimate speaking rate (syllables per second - approximate)
        duration = len(audio) / sample_rate
        speaking_rate = n_voiced_segments / duration if duration > 0 else 0
        
        # Voice/silence ratio
        voice_ratio = np.sum(is_voiced) / len(is_voiced) if len(is_voiced) > 0 else 0
        
        return {
            'speaking_rate': float(speaking_rate),
            'voice_ratio': float(voice_ratio),
            'n_segments': int(n_voiced_segments)
        }
    
    def extract_spectral_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract spectral features (centroid, brightness).
        
        Args:
            audio: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Dictionary with spectral features
        """
        try:
            import librosa
            
            # Compute spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio,
                sr=sample_rate,
                n_fft=2048,
                hop_length=512
            )[0]
            
            # Compute spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio,
                sr=sample_rate,
                n_fft=2048,
                hop_length=512
            )[0]
            
            return {
                'spectral_centroid': float(np.mean(spectral_centroids)),
                'spectral_centroid_std': float(np.std(spectral_centroids)),
                'spectral_rolloff': float(np.mean(spectral_rolloff))
            }
            
        except ImportError:
            logger.warning("librosa not available, skipping spectral features")
            return {
                'spectral_centroid': 0.0,
                'spectral_centroid_std': 0.0,
                'spectral_rolloff': 0.0
            }
        except Exception as e:
            logger.error(f"Error extracting spectral features: {e}")
            return {
                'spectral_centroid': 0.0,
                'spectral_centroid_std': 0.0,
                'spectral_rolloff': 0.0
            }
    
    def extract_all_features(self, filepath: Path) -> Dict[str, float]:
        """Extract all acoustic features from an audio file.
        
        Args:
            filepath: Path to audio file
            
        Returns:
            Dictionary with all extracted features
        """
        logger.info(f"Extracting features from: {filepath}")
        
        # Load audio
        audio, sample_rate = self.load_audio(filepath)
        duration = len(audio) / sample_rate
        
        logger.info(f"  Duration: {duration:.2f}s, Sample rate: {sample_rate}Hz")
        
        # Extract features
        features = {}
        
        # Pitch features
        logger.debug("  Extracting pitch features...")
        pitch_features = self.extract_pitch_features(audio, sample_rate)
        features.update(pitch_features)
        
        # Energy features
        logger.debug("  Extracting energy features...")
        energy_features = self.extract_energy_features(audio, sample_rate)
        features.update(energy_features)
        
        # Temporal features
        logger.debug("  Extracting temporal features...")
        temporal_features = self.extract_temporal_features(audio, sample_rate)
        features.update(temporal_features)
        
        # Spectral features
        logger.debug("  Extracting spectral features...")
        spectral_features = self.extract_spectral_features(audio, sample_rate)
        features.update(spectral_features)
        
        logger.info(f"✓ Extracted {len(features)} features")
        
        return features
    
    def validate_emotional_characteristics(
        self,
        features: Dict[str, float],
        target_coords: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validate that extracted features match expected emotional characteristics.
        
        Args:
            features: Extracted acoustic features
            target_coords: Target emotional coordinates (valence, arousal, tension, stability)
            
        Returns:
            Validation report with recommendations
        """
        report = {
            'expected': {},
            'observed': {},
            'matches': {},
            'warnings': []
        }
        
        valence = target_coords.get('valence', 0)
        arousal = target_coords.get('arousal', 0.5)
        tension = target_coords.get('tension', 0.3)
        stability = target_coords.get('stability', 0.8)
        
        # Arousal → Energy and speaking rate
        report['expected']['high_arousal'] = arousal > 0.7
        report['observed']['high_energy'] = features.get('mean_energy', 0) > 0.1
        report['observed']['high_speaking_rate'] = features.get('speaking_rate', 0) > 5.0
        
        if arousal > 0.7:
            if features.get('mean_energy', 0) < 0.05:
                report['warnings'].append("High arousal expected but energy is low")
            if features.get('speaking_rate', 0) < 3.0:
                report['warnings'].append("High arousal expected but speaking rate is slow")
        
        # Valence → Pitch and spectral brightness
        report['expected']['positive_valence'] = valence > 0.3
        report['observed']['pitch_level'] = features.get('mean_pitch', 0)
        report['observed']['spectral_brightness'] = features.get('spectral_centroid', 0)
        
        # Tension → Pitch variance and energy variance
        report['expected']['high_tension'] = tension > 0.7
        report['observed']['pitch_variance'] = features.get('pitch_variance', 0)
        
        # Stability → Consistency over time
        report['expected']['high_stability'] = stability > 0.7
        report['observed']['pitch_std'] = features.get('pitch_std', 0)
        
        return report


def extract_features_for_anchor(anchor_filepath: Path) -> Dict[str, float]:
    """Convenience function to extract features from an anchor file.
    
    Args:
        anchor_filepath: Path to anchor audio file
        
    Returns:
        Dictionary of extracted features
    """
    extractor = AcousticFeatureExtractor()
    return extractor.extract_all_features(anchor_filepath)
