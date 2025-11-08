import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as FaceDetector from "expo-face-detector";

export default function FaceDetectionScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [isReady, setIsReady] = useState(false);
  const [hasFace, setHasFace] = useState(false);
  const hasAlertedRef = useRef(false);

  useEffect(() => {
    if (permission) {
      console.log(
        "[FaceDetection] Camera permission status:",
        permission.status
      );
    }
  }, [permission]);

  useEffect(() => {
    if (hasFace && !hasAlertedRef.current) {
      hasAlertedRef.current = true;
      Alert.alert("Face detected", "We found a face in the camera view.", [
        {
          text: "OK",
          onPress: () => {
            hasAlertedRef.current = false;
          },
        },
      ]);
    }
  }, [hasFace]);

  const handleFacesDetected = ({ faces }: FaceDetector.DetectionResult) => {
    console.log("[FaceDetection] Faces detected:", faces.length);
    if (faces.length > 0) {
      console.log("[FaceDetection] Example face bounds:", faces[0].bounds);
    }
    setHasFace(faces.length > 0);
    if (faces.length === 0) {
      hasAlertedRef.current = false;
    }
  };

  if (!permission) {
    return (
      <View style={styles.centeredContainer}>
        <ActivityIndicator size="large" />
        <Text style={styles.message}>Checking camera permissions…</Text>
      </View>
    );
  }

  if (!permission.granted) {
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

  return (
    <View style={styles.container}>
      {!isReady && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#fff" />
          <Text style={styles.loadingText}>Preparing camera…</Text>
        </View>
      )}
      <CameraView
        style={StyleSheet.absoluteFill}
        facing="front"
        onCameraReady={() => {
          console.log("[FaceDetection] Camera ready");
          setIsReady(true);
        }}
        {...({
          onFacesDetected: handleFacesDetected,
          faceDetectorEnabled: true,
          faceDetectorSettings: {
            mode: FaceDetector.FaceDetectorMode.fast,
            detectLandmarks: FaceDetector.FaceDetectorLandmarks.none,
            runClassifications: FaceDetector.FaceDetectorClassifications.none,
            minDetectionInterval: 500,
            tracking: true,
          },
        } as Record<string, unknown>)}
      />
      <View style={styles.overlay}>
        <Text style={styles.overlayTitle}>Point the camera towards a face</Text>
        <Text
          style={[
            styles.overlayStatus,
            hasFace ? styles.statusDetected : styles.statusSearching,
          ]}
        >
          {hasFace ? "Face detected!" : "Searching…"}
        </Text>
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
  statusDetected: {
    color: "#34d399",
  },
  statusSearching: {
    color: "#fbbf24",
  },
});
