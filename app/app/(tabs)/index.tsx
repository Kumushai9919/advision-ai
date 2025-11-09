import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useFrameProcessor,
} from "react-native-vision-camera";
import { Worklets } from "react-native-worklets-core";
import {
  useFaceDetector,
  type Face,
} from "react-native-vision-camera-face-detector";
import * as FileSystem from "expo-file-system/legacy";

const formatTimestamp = (date: Date) => {
  const pad = (value: number) => value.toString().padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};

export default function FaceDetectionScreen() {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice("front");
  const cameraRef = useRef<Camera | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [hasFace, setHasFace] = useState(false);
  const [detectionDurationMs, setDetectionDurationMs] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "success" | "error"
  >("idle");
  const detectionStartRef = useRef<number | null>(null);
  const detectionStartTimeRef = useRef<number | null>(null);
  const uploadTriggeredRef = useRef(false);
  const currentFrameTrackingIdRef = useRef<number | undefined>(undefined);
  const lastFaceTrackingIdRef = useRef<number | undefined>(undefined);
  const faceDetectorOptions = useMemo(
    () => ({
      performanceMode: "accurate" as const,
      classificationMode: "all" as const,
      contourMode: "all" as const,
      trackingEnabled: true,
      cameraFacing: device?.position ?? "front",
    }),
    [device?.position]
  );
  const faceDetector = useFaceDetector(faceDetectorOptions);

  const runOnFacesDetected = useMemo(
    () =>
      Worklets.createRunOnJS((faces: Face[]) => {
        console.log("[FaceDetection] Faces detected:", faces.length);
        if (faces.length > 0) {
          const [primaryFace] = faces;
          const { bounds, trackingId } = primaryFace;
          console.log("[FaceDetection] Example face bounds:", bounds);
          currentFrameTrackingIdRef.current = trackingId ?? undefined;
        } else {
          currentFrameTrackingIdRef.current = undefined;
        }

        setHasFace((prev) => {
          const nextHasFace = faces.length > 0;
          if (nextHasFace) {
            const now = Date.now();
            if (detectionStartRef.current == null) {
              detectionStartRef.current = now;
              detectionStartTimeRef.current = now;
              uploadTriggeredRef.current = false;
              setUploadStatus("idle");
              setIsUploading(false);
            }
            setDetectionDurationMs(now - detectionStartRef.current);
          } else {
            detectionStartRef.current = null;
            detectionStartTimeRef.current = null;
            lastFaceTrackingIdRef.current = undefined;
            uploadTriggeredRef.current = false;
            setUploadStatus("idle");
            setIsUploading(false);
            setDetectionDurationMs(0);
          }
          return nextHasFace;
        });
      }),
    []
  );

  const frameProcessor = useFrameProcessor(
    (frame) => {
      "worklet";
      const faces = faceDetector.detectFaces(frame);
      runOnFacesDetected(faces);
    },
    [faceDetector, runOnFacesDetected]
  );

  useEffect(() => {
    return () => {
      faceDetector.stopListeners();
    };
  }, [faceDetector]);

  useEffect(() => {
    if (!device) {
      faceDetector.stopListeners();
    }
  }, [device, faceDetector]);

  const captureAndSendSnapshot = useCallback(async () => {
    if (!cameraRef.current || detectionStartTimeRef.current == null) {
      return;
    }
    let snapshotUri: string | null = null;
    const startTimeMs = detectionStartTimeRef.current;
    try {
      setIsUploading(true);
      const snapshot = await cameraRef.current.takeSnapshot({
        quality: 85,
      });

      snapshotUri = snapshot.path.startsWith("file://")
        ? snapshot.path
        : `file://${snapshot.path}`;

      const imageBase64 = await FileSystem.readAsStringAsync(snapshotUri, {
        encoding: "base64",
      });

      if (startTimeMs == null) {
        throw new Error("Missing detection start time");
      }

      const startDate = new Date(startTimeMs);
      const endDate = new Date();
      const startTime = formatTimestamp(startDate);
      const endTime = formatTimestamp(endDate);
      const durationSeconds = Math.max(
        3,
        Math.round(detectionDurationMs / 1000)
      );

      const imageDataUri = `data:image/jpeg;base64,${imageBase64}`;

      const formData = new FormData();
      formData.append("image_base64", imageDataUri);
      formData.append("start_time", startTime);
      formData.append("end_time", endTime);
      formData.append("duration", durationSeconds.toString());
      formData.append("org_id", "default_org");

      console.log("[FaceDetection] Upload form data", {
        image_base64_length: imageDataUri.length,
        image_base64_sample: imageDataUri.substring(0, 64),
        start_time: startTime,
        end_time: endTime,
        duration: durationSeconds,
        org_id: "default_org",
      });

      const response = await fetch("http://14.138.145.45:8000/api/v1/viewer", {
        method: "POST",
        body: formData,
      });

      const responseText = await response.text();
      console.log("[FaceDetection] Upload response", {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        body: responseText,
      });

      if (!response.ok) {
        throw new Error(
          `Viewer API status ${response.status}: ${responseText || "no body"}`
        );
      }

      setUploadStatus("success");
    } catch (error) {
      console.error("[FaceDetection] Failed to upload viewer payload", error);
      uploadTriggeredRef.current = false;
      setUploadStatus("error");
    } finally {
      setIsUploading(false);
      if (snapshotUri) {
        try {
          await FileSystem.deleteAsync(snapshotUri, { idempotent: true });
        } catch (cleanupError) {
          console.warn(
            "[FaceDetection] Failed to cleanup snapshot file",
            cleanupError
          );
        }
      }
    }
  }, [detectionDurationMs]);

  useEffect(() => {
    const FACE_HOLD_THRESHOLD_MS = 3000;

    if (!hasFace) {
      return;
    }

    const currentTrackingId = currentFrameTrackingIdRef.current;

    if (
      currentTrackingId != null &&
      lastFaceTrackingIdRef.current != null &&
      currentTrackingId !== lastFaceTrackingIdRef.current
    ) {
      // New face detected
      detectionStartRef.current = null;
      detectionStartTimeRef.current = null;
      lastFaceTrackingIdRef.current = undefined;
      uploadTriggeredRef.current = false;
      setUploadStatus("idle");
      setIsUploading(false);
    }

    if (detectionStartRef.current == null) {
      const now = Date.now();
      detectionStartRef.current = now;
      detectionStartTimeRef.current = now;
      uploadTriggeredRef.current = false;
      setUploadStatus("idle");
      setIsUploading(false);
    }

    if (
      detectionDurationMs >= FACE_HOLD_THRESHOLD_MS &&
      !uploadTriggeredRef.current
    ) {
      uploadTriggeredRef.current = true;
      if (currentTrackingId != null) {
        lastFaceTrackingIdRef.current = currentTrackingId;
      }
      captureAndSendSnapshot();
    }
  }, [captureAndSendSnapshot, detectionDurationMs, hasFace]);

  useEffect(() => {
    if (!hasFace) {
      uploadTriggeredRef.current = false;
      lastFaceTrackingIdRef.current = undefined;
    }
  }, [hasFace]);

  if (hasPermission == null) {
    return (
      <View style={styles.centeredContainer}>
        <ActivityIndicator size="large" />
        <Text style={styles.message}>Checking camera permissions…</Text>
      </View>
    );
  }

  if (!hasPermission) {
    return (
      <View style={styles.centeredContainer}>
        <Text style={styles.message}>
          We need camera access to detect faces.
        </Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Grant camera permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.centeredContainer}>
        <ActivityIndicator size="large" />
        <Text style={styles.message}>
          Looking for a compatible front camera…
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {!isReady && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#fff" />
          <Text style={styles.loadingText}>Preparing camera…</Text>
        </View>
      )}
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive
        photo
        frameProcessor={frameProcessor}
        onInitialized={() => {
          console.log("[FaceDetection] Camera ready");
          setIsReady(true);
        }}
      />
      <View style={styles.overlay}>
        <Text style={styles.overlayTitle}>Point the camera towards a face</Text>
        <Text
          style={[
            styles.overlayStatus,
            hasFace ? styles.statusDetected : styles.statusSearching,
          ]}
        >
          {hasFace
            ? `Face detected for ${(detectionDurationMs / 1000).toFixed(1)}s`
            : "Searching…"}
        </Text>
        {hasFace && (
          <Text style={styles.overlaySubStatus}>
            {isUploading
              ? "Uploading snapshot…"
              : uploadStatus === "success"
              ? "Snapshot sent"
              : uploadStatus === "error"
              ? "Upload failed – hold steady to retry"
              : "Hold steady for 3 seconds to capture"}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  centeredContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#0b0b0b",
  },
  message: {
    color: "#fff",
    textAlign: "center",
    marginTop: 16,
    fontSize: 16,
  },
  button: {
    marginTop: 24,
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: "#2563eb",
    borderRadius: 8,
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.6)",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 2,
  },
  loadingText: {
    color: "#fff",
    marginTop: 12,
    fontSize: 16,
  },
  overlay: {
    position: "absolute",
    bottom: 60,
    left: 0,
    right: 0,
    alignItems: "center",
    paddingHorizontal: 16,
  },
  overlayTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 8,
  },
  overlayStatus: {
    fontSize: 24,
    fontWeight: "700",
  },
  overlaySubStatus: {
    marginTop: 8,
    color: "#e5e7eb",
    fontSize: 16,
  },
  statusDetected: {
    color: "#34d399",
  },
  statusSearching: {
    color: "#fbbf24",
  },
});
