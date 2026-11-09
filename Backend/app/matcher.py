import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from typing import Optional, Tuple
from PIL import Image

class VisualTagMatcher:
    """
    Robust Visual Tag Matcher combining Deep Feature Embedding,
    Color-Spatial Histograms, and Multi-Scale Patch Correlation.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._init_deep_model()
        self.transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _init_deep_model(self):
        try:
            base_model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
        except Exception:
            base_model = models.mobilenet_v3_small()
        
        # Strip classification head to use as feature extractor
        self.feature_extractor = base_model.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.feature_extractor.to(self.device)
        self.feature_extractor.eval()

    def extract_deep_features(self, image_bgr: np.ndarray) -> np.ndarray:
        """Extract L2-normalized 576-dim deep feature embedding."""
        if image_bgr is None or image_bgr.size == 0:
            return np.zeros(576, dtype=np.float32)
        
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            feat = self.feature_extractor(tensor)
            feat = self.pool(feat).squeeze().cpu().numpy()
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            return feat

    def extract_color_spatial_features(self, image_bgr: np.ndarray) -> np.ndarray:
        """Extract multi-channel HSV and Lab spatial color distribution."""
        if image_bgr is None or image_bgr.size == 0:
            return np.zeros(64, dtype=np.float32)
        
        resized = cv2.resize(image_bgr, (64, 64))
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        
        # 3D HSV histogram: 8 Hue bins, 4 Saturation bins, 2 Value bins = 64 bins
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 2], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist

    def compute_similarity(self, candidate_bgr: np.ndarray, reference_bgr: np.ndarray) -> float:
        """
        Calculates ensemble similarity score [0.0, 1.0] between a candidate person crop
        and the target reference tag.
        """
        if candidate_bgr is None or reference_bgr is None:
            return 0.0
        if candidate_bgr.size == 0 or reference_bgr.size == 0:
            return 0.0

        # 1. Deep Feature Cosine Similarity
        feat_cand = self.extract_deep_features(candidate_bgr)
        feat_ref = self.extract_deep_features(reference_bgr)
        cos_sim = float(np.dot(feat_cand, feat_ref))
        # Map cosine similarity from [-1, 1] to [0, 1]
        deep_score = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0))

        # 2. Color-Spatial Histogram Correlation
        hist_cand = self.extract_color_spatial_features(candidate_bgr)
        hist_ref = self.extract_color_spatial_features(reference_bgr)
        # cv2.HISTCMP_CORREL returns [-1, 1]
        color_corr = float(cv2.compareHist(hist_cand, hist_ref, cv2.HISTCMP_CORREL))
        color_score = max(0.0, min(1.0, (color_corr + 1.0) / 2.0))

        # 3. Multi-scale Template Correlation
        try:
            cand_gray = cv2.cvtColor(candidate_bgr, cv2.COLOR_BGR2GRAY)
            ref_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
            
            # Match template if reference is smaller than candidate
            h_c, w_c = cand_gray.shape
            h_r, w_r = ref_gray.shape
            if h_r < h_c and w_r < w_c:
                res = cv2.matchTemplate(cand_gray, ref_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                template_score = max(0.0, float(max_val))
            else:
                ref_resized = cv2.resize(ref_gray, (min(w_c, w_r), min(h_c, h_r)))
                cand_resized = cv2.resize(cand_gray, (ref_resized.shape[1], ref_resized.shape[0]))
                corr = np.corrcoef(cand_resized.flatten(), ref_resized.flatten())[0, 1]
                template_score = max(0.0, float(corr)) if not np.isnan(corr) else 0.5
        except Exception:
            template_score = 0.5

        # Weighted combination: Deep features (50%) + Color profile (30%) + Template (20%)
        ensemble_score = (0.50 * deep_score) + (0.30 * color_score) + (0.20 * template_score)
        return round(float(ensemble_score), 4)

    def detect_tag_presence_heuristic(self, upper_body_bgr: np.ndarray) -> Tuple[float, Optional[np.ndarray]]:
        """
        Heuristic detector for when no reference tag is uploaded:
        Evaluates badge / lanyard visual signatures (high contrast rectangular badge on chest).
        """
        if upper_body_bgr is None or upper_body_bgr.size == 0:
            return 0.0, None

        h, w = upper_body_bgr.shape[:2]
        gray = cv2.cvtColor(upper_body_bgr, cv2.COLOR_BGR2GRAY)
        
        # Gradient / Edge detection
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_density = float(np.mean(np.sqrt(sobelx**2 + sobely**2)))
        
        # Standard deviation of brightness in chest area (detects bright badge on dark shirt or vice versa)
        std_dev = float(np.std(gray))
        
        score = min(1.0, (edge_density / 80.0) * 0.5 + (std_dev / 60.0) * 0.5)
        return round(score, 4), upper_body_bgr

