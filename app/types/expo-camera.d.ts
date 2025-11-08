import type { DetectionOptions, DetectionResult } from "expo-face-detector";

declare module "expo-camera" {
  interface CameraViewProps {
    /**
     * Enables or disables the face detector.
     */
    faceDetectorEnabled?: boolean;
    /**
     * Settings passed to the face detector.
     */
    faceDetectorSettings?: DetectionOptions;
    /**
     * Invoked when faces are detected in the camera preview.
     */
    onFacesDetected?: (result: DetectionResult) => void;
  }
}
