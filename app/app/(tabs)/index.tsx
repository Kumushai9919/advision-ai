import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
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
import { runOnJS } from "react-native-reanimated";
import { useFocusEffect } from "@react-navigation/native";
import { scanFaces, type Face } from "vision-camera-face-detector";

export default function FaceDetectionScreen() {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice("front");
  const [isScreenFocused, setIsScreenFocused] = useState(true);
  const [isCameraInitialized, setIsCameraInitialized] = useState(false);
  const [hasFace, setHasFace] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Searching…");
  const [logs, setLogs] = useState<string[]>([]);
  const [lastDetectionDuration, setLastDetectionDuration] = useState<
    string | null
  >(null);
  const hasAlertedRef = useRef(false);
  const permissionRequestedRef = useRef(false);
  const toastResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const detectionStartRef = useRef<number | null>(null);

  useFocusEffect(
    useCallback(() => {
      setIsScreenFocused(true);
      return () => setIsScreenFocused(false);
    }, [])
  );

  useEffect(() => {
    console.log(
      "[FaceDetection] Camera permission status:",
      hasPermission ? "granted" : "not granted"
    );
    setLogs((current) => [
      `[${new Date().toLocaleTimeString()}] Permission: ${
        hasPermission ? "granted" : "not granted"
      }`,
      ...current,
    ]);
  }, [hasPermission]);

  useEffect(() => {
    if (!hasPermission && !permissionRequestedRef.current) {
      permissionRequestedRef.current = true;
      void requestPermission();
    }
  }, [hasPermission, requestPermission]);

  const pushLog = useCallback((message: string) => {
    setLogs((current) => {
      const entry = `[${new Date().toLocaleTimeString()}] ${message}`;
      return [entry, ...current].slice(0, 6);
    });
  }, []);

  const handleFaces = useCallback(
    (faces: Face[]) => {
      console.log("[FaceDetection] Faces detected:", faces.length);
      if (faces.length > 0) {
        console.log("[FaceDetection] Example face bounds:", faces[0].bounds);
      }

      setHasFace(faces.length > 0);
      if (faces.length === 0) {
        setStatusMessage("Searching…");
        pushLog("No faces in frame");
        hasAlertedRef.current = false;
        if (detectionStartRef.current != null) {
          const durationMs = Date.now() - detectionStartRef.current;
          const seconds = (durationMs / 1000).toFixed(1);
          setLastDetectionDuration(`${seconds}s`);
          pushLog(`Face lost after ${seconds}s`);
          detectionStartRef.current = null;
        }
        if (toastResetTimeoutRef.current) {
          clearTimeout(toastResetTimeoutRef.current);
          toastResetTimeoutRef.current = null;
        }
      } else {
        setStatusMessage("Face detected!");
        if (detectionStartRef.current == null) {
          detectionStartRef.current = Date.now();
          setLastDetectionDuration(null);
          pushLog(`Face entered (${faces.length})`);
        }
        if (!hasAlertedRef.current) {
          hasAlertedRef.current = true;
          pushLog(`Detected ${faces.length} face(s)`);
          if (toastResetTimeoutRef.current) {
            clearTimeout(toastResetTimeoutRef.current);
          }
          toastResetTimeoutRef.current = setTimeout(() => {
            hasAlertedRef.current = false;
            toastResetTimeoutRef.current = null;
          }, 2500);
        }
      }
    },
    [pushLog]
  );

  const frameProcessor = useFrameProcessor(
    (frame) => {
      "worklet";
      const detectedFaces = scanFaces(frame);
      runOnJS(handleFaces)(detectedFaces);
    },
    [handleFaces]
  );

  const isCameraActive = useMemo(() => {
    return Boolean(hasPermission && device && isScreenFocused);
  }, [device, hasPermission, isScreenFocused]);

  useEffect(() => {
    return () => {
      if (toastResetTimeoutRef.current) {
        clearTimeout(toastResetTimeoutRef.current);
        toastResetTimeoutRef.current = null;
      }
    };
  }, []);

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

  if (device == null) {
    return (
      <View style={styles.centeredContainer}>
        <ActivityIndicator size="large" />
        <Text style={styles.message}>Loading camera…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {!isCameraInitialized && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#fff" />
          <Text style={styles.loadingText}>Preparing camera…</Text>
        </View>
      )}
      <Camera
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={isCameraActive}
        onInitialized={() => {
          console.log("[FaceDetection] VisionCamera initialized");
          pushLog("Camera ready");
          setStatusMessage("Searching…");
          setIsCameraInitialized(true);
        }}
        frameProcessor={frameProcessor}
      />
      <View style={styles.logPanel}>
        <Text style={styles.logTitle}>Live Logs</Text>
        <ScrollView
          style={styles.logScroll}
          contentContainerStyle={styles.logContent}
        >
          {logs.length === 0 ? (
            <Text style={styles.logEmpty}>Waiting for events…</Text>
          ) : (
            logs.map((log, index) => (
              <Text style={styles.logEntry} key={index}>
                {log}
              </Text>
            ))
          )}
        </ScrollView>
      </View>
      <View style={styles.overlay}>
        <Text style={styles.overlayTitle}>Point the camera towards a face</Text>
        <Text
          style={[
            styles.overlayStatus,
            hasFace ? styles.statusDetected : styles.statusSearching,
          ]}
        >
          {statusMessage}
        </Text>
        {lastDetectionDuration && (
          <Text style={styles.overlayDuration}>
            Last detection: {lastDetectionDuration}
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
  overlayDuration: {
    marginTop: 8,
    color: "#93c5fd",
    fontSize: 16,
    fontWeight: "500",
  },
  statusDetected: {
    color: "#34d399",
  },
  statusSearching: {
    color: "#fbbf24",
  },
  logPanel: {
    position: "absolute",
    top: 60,
    left: 20,
    right: 20,
    maxHeight: 160,
    backgroundColor: "rgba(17, 24, 39, 0.85)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "rgba(59, 130, 246, 0.35)",
  },
  logTitle: {
    color: "#93c5fd",
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 6,
  },
  logScroll: {
    maxHeight: 110,
  },
  logContent: {
    gap: 4,
  },
  logEntry: {
    color: "#e5e7eb",
    fontSize: 12,
  },
  logEmpty: {
    color: "#9ca3af",
    fontSize: 12,
    fontStyle: "italic",
  },
});
