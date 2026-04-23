import { useEffect, useRef, useState } from "react";
import LiveFeed from "../components/LiveFeed";
import { createRecognitionSocket } from "../services/websocket";
import { videoApi } from "../services/api";

export default function LiveRecognitionPage() {
  const [events, setEvents] = useState([]);
  const [sourceType, setSourceType] = useState("webcam");
  const [sourcePath, setSourcePath] = useState("");
  const [videoFile, setVideoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [remotePreviewImage, setRemotePreviewImage] = useState("");
  const [previewMode, setPreviewMode] = useState("idle");
  const [latestFaces, setLatestFaces] = useState([]);
  const [frameSize, setFrameSize] = useState({ width: 1, height: 1 });
  const [currentFps, setCurrentFps] = useState(0);
  const [processingMs, setProcessingMs] = useState(0);
  const socketRef = useRef(null);
  const frameIntervalRef = useRef(null);
  const lastRecognitionTsRef = useRef(0);
  const previewObjectUrlRef = useRef(null);
  const webcamStreamRef = useRef(null);
  const videoRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const popupWindowRef = useRef(null);

  const getPrimaryFace = () => {
    if (!Array.isArray(latestFaces) || latestFaces.length === 0) {
      return null;
    }
    return latestFaces.reduce((best, current) => {
      const bestScore = Number(best?.confidence || 0);
      const currentScore = Number(current?.confidence || 0);
      return currentScore > bestScore ? current : best;
    }, latestFaces[0]);
  };

  const formatFaceDetails = (face) => {
    if (!face) {
      return "No person detected";
    }
    const details = face.person_details || {};
    const parts = [
      `Name: ${face.name || details.name || "Unknown"}`,
      `ID: ${face.person_id ?? details.person_id ?? "-"}`,
      `Department: ${details.department || "-"}`,
      `Email: ${details.email || "-"}`,
      `Confidence: ${Number(face.confidence || 0).toFixed(2)}`,
      `Status: ${face.message || "No match"}`,
    ];
    return parts.join(" | ");
  };

  const syncPopupPreview = () => {
    const popup = popupWindowRef.current;
    if (!popup || popup.closed) {
      popupWindowRef.current = null;
      return;
    }

    const doc = popup.document;
    const popupTitle = doc.getElementById("previewTitle");
    const popupImage = doc.getElementById("previewImage");
    const popupVideo = doc.getElementById("previewVideo");
    const popupStats = doc.getElementById("previewStats");
    const popupDetails = doc.getElementById("previewDetails");
    const popupHint = doc.getElementById("previewHint");
    const popupCanvas = doc.getElementById("previewCanvas");
    if (!popupTitle || !popupImage || !popupVideo || !popupStats || !popupDetails || !popupHint || !popupCanvas) {
      return;
    }

    popupTitle.textContent = "Live Preview";
    popupStats.textContent = `FPS: ${currentFps.toFixed(2)} | Processing: ${processingMs.toFixed(2)} ms | Faces: ${latestFaces.length}`;
    popupDetails.textContent = formatFaceDetails(getPrimaryFace());

    // Draw bounding boxes on canvas overlay
    const ctx = popupCanvas.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, popupCanvas.width, popupCanvas.height);
      
      const previewContainer = doc.querySelector(".preview");
      if (previewContainer && frameSize.width > 1 && frameSize.height > 1) {
        const containerRect = previewContainer.getBoundingClientRect();
        const scaleX = containerRect.width / frameSize.width;
        const scaleY = containerRect.height / frameSize.height;
        
        if (Array.isArray(latestFaces) && latestFaces.length > 0) {
          latestFaces.forEach((face, idx) => {
            if (!Array.isArray(face.bbox) || face.bbox.length < 4) return;
            
            const [x1, y1, x2, y2] = face.bbox;
            const drawX = x1 * scaleX;
            const drawY = y1 * scaleY;
            const drawW = (x2 - x1) * scaleX;
            const drawH = (y2 - y1) * scaleY;
            
            // Draw bounding box
            ctx.strokeStyle = "#22c55e";
            ctx.lineWidth = 2;
            ctx.strokeRect(drawX, drawY, drawW, drawH);
            
            // Draw label background
            const label = `${face.name || "Unknown"} (${Number(face.confidence || 0).toFixed(2)})`;
            ctx.font = "12px sans-serif";
            const metrics = ctx.measureText(label);
            const labelHeight = 18;
            const labelPadding = 4;
            
            ctx.fillStyle = "rgba(34, 197, 94, 0.9)";
            ctx.fillRect(drawX, Math.max(0, drawY - labelHeight), metrics.width + 2 * labelPadding, labelHeight);
            
            // Draw label text
            ctx.fillStyle = "#000";
            ctx.fillText(label, drawX + labelPadding, drawY - 5);
          });
        }
      }
    }

    if (previewMode === "remote" && remotePreviewImage) {
      popupImage.style.display = "block";
      popupVideo.style.display = "none";
      popupHint.style.display = "none";
      popupCanvas.style.display = "block";
      popupImage.src = remotePreviewImage;
      return;
    }

    if (previewMode === "file" && previewUrl) {
      popupImage.style.display = "none";
      popupVideo.style.display = "block";
      popupHint.style.display = "none";
      popupCanvas.style.display = "block";
      if (popupVideo.src !== previewUrl) {
        popupVideo.src = previewUrl;
      }
      popupVideo.controls = true;
      popupVideo.loop = true;
      popupVideo.muted = true;
      popupVideo.play().catch(() => {});
      return;
    }

    if (previewMode === "webcam" && webcamStreamRef.current) {
      popupImage.style.display = "none";
      popupVideo.style.display = "block";
      popupHint.style.display = "none";
      popupCanvas.style.display = "block";
      if (popupVideo.srcObject !== webcamStreamRef.current) {
        popupVideo.srcObject = webcamStreamRef.current;
      }
      popupVideo.controls = false;
      popupVideo.muted = true;
      popupVideo.play().catch(() => {});
      return;
    }

    popupImage.style.display = "none";
    popupVideo.style.display = "none";
    popupHint.style.display = "block";
    popupCanvas.style.display = "none";
    popupHint.textContent = "Start processing to show preview";
  };

  const openPopupPreview = () => {
    const existing = popupWindowRef.current;
    if (existing && !existing.closed) {
      existing.focus();
      syncPopupPreview();
      return;
    }

    const popup = window.open("", "live-preview-popup", "width=1100,height=760,resizable=yes");
    if (!popup) {
      setStatusMessage("Popup blocked by browser. Allow popups and try again.");
      return;
    }

    popup.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8" />
        <title>Live Preview</title>
        <style>
          body { margin: 0; background: #0f172a; color: #e2e8f0; font-family: Segoe UI, sans-serif; }
          .wrap { display: flex; flex-direction: column; height: 100vh; width: 100vw; }
          .header { padding: 12px 16px; background: #111827; border-bottom: 1px solid #1f2937; flex-shrink: 0; }
          .title { font-size: 16px; font-weight: 600; margin: 0 0 4px 0; }
          .stats { font-size: 12px; color: #cbd5e1; }
          .preview { position: relative; flex: 1; display: flex; align-items: center; justify-content: center; background: #000; overflow: hidden; width: 100%; height: 100%; }
          .preview img, .preview video { width: 100%; height: 100%; object-fit: contain; }
          #previewCanvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
          .hint { color: #94a3b8; font-size: 14px; }
          .footer { padding: 12px 16px; background: #0b1220; border-top: 1px solid #1f2937; font-size: 13px; flex-shrink: 0; overflow-y: auto; max-height: 80px; }
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="header">
            <div id="previewTitle" class="title">Live Preview</div>
            <div id="previewStats" class="stats">FPS: 0.00 | Processing: 0.00 ms | Faces: 0</div>
          </div>
          <div class="preview">
            <img id="previewImage" alt="Live preview frame" style="display:none" />
            <video id="previewVideo" playsinline autoplay muted style="display:none"></video>
            <canvas id="previewCanvas" style="display:none"></canvas>
            <div id="previewHint" class="hint">Start processing to show preview</div>
          </div>
          <div id="previewDetails" class="footer">No person detected</div>
        </div>
      </body>
      </html>
    `);
    popup.document.close();
    popupWindowRef.current = popup;
    
    // Initialize canvas dimensions
    const popupCanvas = popup.document.getElementById("previewCanvas");
    if (popupCanvas) {
      const previewDiv = popup.document.querySelector(".preview");
      if (previewDiv) {
        popupCanvas.width = previewDiv.offsetWidth || 1100;
        popupCanvas.height = previewDiv.offsetHeight || 700;
        
        // Redraw canvas on window resize
        popup.addEventListener("resize", () => {
          if (popupCanvas) {
            popupCanvas.width = previewDiv.offsetWidth || popupCanvas.width;
            popupCanvas.height = previewDiv.offsetHeight || popupCanvas.height;
            syncPopupPreview();
          }
        });
      }
    }
    
    syncPopupPreview();
  };

  const stopBrowserFrameStream = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  };

  const startBrowserFrameStream = () => {
    stopBrowserFrameStream();
    frameIntervalRef.current = setInterval(() => {
      const socket = socketRef.current;
      const video = videoRef.current;
      const canvas = captureCanvasRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN || !video || !canvas) return;
      if (video.videoWidth <= 0 || video.videoHeight <= 0) return;

      const targetWidth = 640;
      const ratio = video.videoHeight / video.videoWidth;
      const targetHeight = Math.max(1, Math.round(targetWidth * ratio));
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
      const image = canvas.toDataURL("image/jpeg", 0.75);
      socket.send(JSON.stringify({ type: "frame", image }));
    }, 700);
  };

  const stopLocalPreview = () => {
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach((track) => track.stop());
      webcamStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setPreviewMode("idle");
  };

  const startLocalPreview = async () => {
    stopLocalPreview();
    if (sourceType === "webcam") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        webcamStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setPreviewMode("webcam");
      } catch {
        setStatusMessage("Failed to open webcam preview.");
      }
      return;
    }

    if (sourceType === "file") {
      if (previewUrl) {
        setPreviewMode("file");
      } else {
        setRemotePreviewImage("");
        setPreviewMode("remote");
      }
      return;
    }

    if (sourceType === "rtsp") {
      setRemotePreviewImage("");
      setPreviewMode("remote");
      return;
    }

    setPreviewMode("idle");
  };

  useEffect(() => {
    return () => {
      stopBrowserFrameStream();
      stopLocalPreview();
      if (popupWindowRef.current && !popupWindowRef.current.closed) {
        popupWindowRef.current.close();
      }
      if (previewObjectUrlRef.current) {
        URL.revokeObjectURL(previewObjectUrlRef.current);
        previewObjectUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    syncPopupPreview();
  }, [previewMode, remotePreviewImage, previewUrl, latestFaces, currentFps, processingMs]);

  useEffect(() => {
    if (!videoRef.current) return;

    if (previewMode === "webcam" && webcamStreamRef.current) {
      videoRef.current.srcObject = webcamStreamRef.current;
      videoRef.current.play().catch(() => {});
      return;
    }

    if (previewMode === "file") {
      videoRef.current.srcObject = null;
      videoRef.current.play().catch(() => {});
      return;
    }

    videoRef.current.srcObject = null;
  }, [previewMode, previewUrl]);

  const uploadVideo = async () => {
    if (!videoFile) {
      setStatusMessage("Choose a video file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", videoFile);
    setUploading(true);
    setStatusMessage("");

    try {
      const { data } = await videoApi.upload(formData);
      setSourceType("file");
      setSourcePath(data.video_path || "");
      setStatusMessage("Video uploaded. You can start live processing now.");
      await startLocalPreview();
    } catch (error) {
      setStatusMessage(error?.response?.data?.detail || "Video upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const start = async () => {
    if (sourceType === "file" && !sourcePath) {
      setStatusMessage("Upload a video or enter a valid server file path.");
      return;
    }
    if (sourceType === "rtsp" && !sourcePath.trim()) {
      setStatusMessage("Enter a valid RTSP URL before starting.");
      return;
    }
    setFrameSize({ width: 1, height: 1 });
    await startLocalPreview();
    stopBrowserFrameStream();
    if (socketRef.current) {
      socketRef.current.close();
    }

    const wsSourceType = sourceType === "webcam" ? "browser_webcam" : sourceType;
    const shouldUseRemotePreview = sourceType === "rtsp" || (sourceType === "file" && !previewUrl);
    const socket = createRecognitionSocket(
      { source_type: wsSourceType, source_path: sourcePath || null },
      (payload) => {
        if (payload.type === "recognition") {
          const now = performance.now();
          if (lastRecognitionTsRef.current > 0) {
            const delta = now - lastRecognitionTsRef.current;
            if (delta > 0) {
              setCurrentFps(Number((1000 / delta).toFixed(2)));
            }
          }
          lastRecognitionTsRef.current = now;

          const faces = Array.isArray(payload.faces) ? payload.faces : [];
          if (faces.length > 0) {
            const faceEvents = faces.map((face) => ({
              ...payload,
              person_id: face.person_id,
              name: face.name,
              person_details: face.person_details,
              confidence: face.confidence,
              target_confidence: payload.target_confidence,
              meets_target: face.meets_target,
              attendance_marked: face.attendance_marked,
              message: face.message,
              bbox: face.bbox,
            }));
            setEvents((prev) => [...faceEvents, ...prev].slice(0, 200));
          }
          setLatestFaces(faces);
          setProcessingMs(Number(payload.processing_ms || 0));
          if (payload.frame_width && payload.frame_height) {
            setFrameSize({ width: payload.frame_width, height: payload.frame_height });
          }
          if (shouldUseRemotePreview && typeof payload.preview_image === "string" && payload.preview_image) {
            setRemotePreviewImage(payload.preview_image);
            setPreviewMode("remote");
          }
          return;
        }

        if (payload.type === "error") {
          setStatusMessage(payload.message || "Stream processing failed.");
          return;
        }

        if (payload.type === "done") {
          setStatusMessage("Stream completed.");
        }
      },
      () => {
        stopBrowserFrameStream();
        socketRef.current = null;
      }
    );
    if (sourceType === "webcam") {
      setStatusMessage("Processing started using browser webcam.");
      socketRef.current = socket;
      startBrowserFrameStream();
      return;
    }
    setStatusMessage(shouldUseRemotePreview ? "Processing started. Waiting for stream preview..." : "Processing started.");
    socketRef.current = socket;
  };

  const stop = () => {
    stopBrowserFrameStream();
    if (socketRef.current?.readyState === WebSocket.OPEN && sourceType === "webcam") {
      socketRef.current.send(JSON.stringify({ type: "stop" }));
    }
    socketRef.current?.close();
    socketRef.current = null;
    stopLocalPreview();
    setRemotePreviewImage("");
    setLatestFaces([]);
    setFrameSize({ width: 1, height: 1 });
    setCurrentFps(0);
    setProcessingMs(0);
    lastRecognitionTsRef.current = 0;
    setStatusMessage("Processing stopped.");
  };

  const clearEvents = () => {
    setEvents([]);
    setLatestFaces([]);
    setCurrentFps(0);
    setProcessingMs(0);
    lastRecognitionTsRef.current = 0;
    setStatusMessage("Events cleared.");
  };

  const handleVideoFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setVideoFile(file);
    if (previewObjectUrlRef.current) {
      URL.revokeObjectURL(previewObjectUrlRef.current);
      previewObjectUrlRef.current = null;
    }
    if (file) {
      const objectUrl = URL.createObjectURL(file);
      previewObjectUrlRef.current = objectUrl;
      setPreviewUrl(objectUrl);
      setSourceType("file");
    } else {
      setPreviewUrl("");
    }
  };

  const getBoxStyle = (bbox) => ({
    left: `${(bbox[0] / frameSize.width) * 100}%`,
    top: `${(bbox[1] / frameSize.height) * 100}%`,
    width: `${((bbox[2] - bbox[0]) / frameSize.width) * 100}%`,
    height: `${((bbox[3] - bbox[1]) / frameSize.height) * 100}%`,
  });

  const showVideoPreview = previewMode === "webcam" || previewMode === "file";
  const showRemotePreview = previewMode === "remote" && Boolean(remotePreviewImage);
  const showPlaceholder = previewMode === "idle" || (previewMode === "remote" && !remotePreviewImage);
  const primaryFace = getPrimaryFace();
  const primaryDetails = primaryFace?.person_details || {};
  const previewAspectRatio = frameSize.width > 1 && frameSize.height > 1
    ? `${frameSize.width} / ${frameSize.height}`
    : "16 / 9";

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap gap-2 items-end">
        <label className="flex flex-col text-sm">
          Source Type
          <select className="border rounded p-2" value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
            <option value="webcam">Webcam</option>
            <option value="file">Video File</option>
            <option value="rtsp">RTSP</option>
          </select>
        </label>
        <label className="flex flex-col text-sm grow">
          Source Path
          <input className="border rounded p-2" value={sourcePath} onChange={(e) => setSourcePath(e.target.value)} />
        </label>
        <label className="flex flex-col text-sm grow">
          Add Video
          <input
            type="file"
            accept="video/mp4,video/avi,video/quicktime,video/x-matroska,video/webm"
            className="border rounded p-2"
            onChange={handleVideoFileChange}
          />
        </label>
        <button onClick={uploadVideo} className="rounded bg-accent text-white px-4 py-2" disabled={uploading}>
          {uploading ? "Uploading..." : "Upload Video"}
        </button>
        <button onClick={start} className="rounded bg-mint text-white px-4 py-2">Start</button>
        <button onClick={stop} className="rounded bg-slate-700 text-white px-4 py-2">Stop</button>
        <button onClick={openPopupPreview} className="rounded bg-indigo-600 text-white px-4 py-2">Open Preview Popup</button>
      </div>
      {statusMessage ? <div className="card text-sm">{statusMessage}</div> : null}

      <div className="card flex flex-col">
        <h3 className="font-display text-lg mb-3">Live Preview</h3>
        <canvas ref={captureCanvasRef} className="hidden" />
        <div className="relative w-full flex-1 min-h-[300px] rounded-xl overflow-hidden bg-black" style={{ aspectRatio: previewAspectRatio, maxHeight: "calc(100vh - 300px)" }}>
          <video
            ref={videoRef}
            className={`w-full h-full object-contain ${showVideoPreview ? "block" : "hidden"}`}
            autoPlay
            muted
            playsInline
            controls={previewMode === "file"}
            loop={previewMode === "file"}
            src={previewMode === "file" ? previewUrl : undefined}
          />
          {showRemotePreview ? (
            <img src={remotePreviewImage} alt="RTSP stream preview" className="w-full h-full object-contain" />
          ) : null}
          {showPlaceholder ? (
            <div className="absolute inset-0 flex items-center justify-center text-slate-200 text-sm">
              {previewMode === "remote" ? "Waiting for stream frames..." : "Start processing to show preview"}
            </div>
          ) : null}

          {previewMode !== "idle" ? (
            <div className="absolute top-2 left-2 bg-black/70 text-white text-xs rounded px-2 py-1 space-y-0.5">
              <div>FPS: {currentFps.toFixed(2)}</div>
              <div>Processing: {processingMs.toFixed(2)} ms</div>
              <div>Faces: {latestFaces.length}</div>
            </div>
          ) : null}

          {latestFaces.map((face, idx) => {
            if (!Array.isArray(face.bbox) || face.bbox.length < 4) {
              return null;
            }
            const boxStyle = getBoxStyle(face.bbox);
            const label = `${face.name || "Unknown"} (${Number(face.confidence || 0).toFixed(2)})`;
            return (
              <div key={`face-${idx}`}>
                <div className="absolute border-2 border-lime-400" style={boxStyle} />
                <div
                  className="absolute bg-lime-500/90 text-black text-xs font-semibold px-2 py-1 rounded"
                  style={{
                    left: boxStyle.left,
                    top: `calc(${boxStyle.top} - 28px)`,
                  }}
                >
                  {label}
                </div>
              </div>
            );
          })}

          {previewMode !== "idle" ? (
            <div className="absolute left-0 right-0 bottom-0 bg-black/75 text-slate-100 text-xs px-3 py-2">
              {primaryFace ? (
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  <span className="font-semibold">{primaryFace.name || primaryDetails.name || "Unknown"}</span>
                  <span>ID: {primaryFace.person_id ?? primaryDetails.person_id ?? "-"}</span>
                  <span>Department: {primaryDetails.department || "-"}</span>
                  <span>Email: {primaryDetails.email || "-"}</span>
                  <span>Confidence: {Number(primaryFace.confidence || 0).toFixed(2)}</span>
                  <span>Status: {primaryFace.message || "No match"}</span>
                </div>
              ) : (
                <div>No person detected</div>
              )}
            </div>
          ) : null}
        </div>
      </div>

      <LiveFeed events={events} onClear={clearEvents} />
    </div>
  );
}
