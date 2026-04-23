import { useEffect, useState } from "react";
import { personApi, trainingApi } from "../services/api";

export default function TrainingPage() {
  const [status, setStatus] = useState(null);
  const [quality, setQuality] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingQuality, setLoadingQuality] = useState(false);
  const [message, setMessage] = useState("");
  const [persons, setPersons] = useState([]);
  const [selectedPersonId, setSelectedPersonId] = useState(null);
  const [personImages, setPersonImages] = useState([]);
  const [loadingImages, setLoadingImages] = useState(false);
  const [deletingImageId, setDeletingImageId] = useState(null);

  const load = async () => {
    const [statusRes, qualityRes, logsRes, personsRes] = await Promise.all([
      trainingApi.status(),
      trainingApi.quality(),
      trainingApi.logs(),
      personApi.list(),
    ]);
    setStatus(statusRes.data);
    setQuality(qualityRes.data);
    setLogs(logsRes.data || []);
    const allPersons = personsRes.data || [];
    setPersons(allPersons);
    if (!selectedPersonId && allPersons.length > 0) {
      setSelectedPersonId(allPersons[0].id);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const refreshQuality = async () => {
    setLoadingQuality(true);
    try {
      const { data } = await trainingApi.quality();
      setQuality(data);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load training quality summary.");
    } finally {
      setLoadingQuality(false);
    }
  };

  const trigger = async () => {
    setLoading(true);
    setMessage("");
    try {
      await trainingApi.trigger();
      await load();
      setMessage("Training completed and logs refreshed.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Training failed.");
    } finally {
      setLoading(false);
    }
  };

  const deletePersonImage = async (imageId) => {
    if (!imageId) return;
    setMessage("");
    setDeletingImageId(imageId);
    try {
      await personApi.deleteImage(imageId);
      setMessage("Image deleted successfully.");
      await loadPersonImages(selectedPersonId);
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to delete image.");
    } finally {
      setDeletingImageId(null);
    }
  };

  const loadPersonImages = async (personId) => {
    if (!personId) {
      setPersonImages([]);
      return;
    }
    setLoadingImages(true);
    try {
      const { data } = await personApi.listImages(personId);
      const images = data || [];
      const previews = await Promise.all(
        images.map(async (img) => {
          try {
            const response = await personApi.previewImage(img.id);
            return {
              ...img,
              previewUrl: URL.createObjectURL(response.data),
            };
          } catch {
            return {
              ...img,
              previewUrl: "",
            };
          }
        })
      );
      setPersonImages((prev) => {
        prev.forEach((img) => {
          if (img.previewUrl) {
            URL.revokeObjectURL(img.previewUrl);
          }
        });
        return previews;
      });
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Failed to load person images.");
      setPersonImages((prev) => {
        prev.forEach((img) => {
          if (img.previewUrl) {
            URL.revokeObjectURL(img.previewUrl);
          }
        });
        return [];
      });
    } finally {
      setLoadingImages(false);
    }
  };

  useEffect(() => {
    loadPersonImages(selectedPersonId);
  }, [selectedPersonId]);

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="font-display text-lg mb-3">Training Interface</h3>
        <button disabled={loading} onClick={trigger} className="rounded bg-accent text-white px-4 py-2">
          {loading ? "Training..." : "Trigger Training"}
        </button>
        {status && (
          <div className="mt-3 text-sm">
            Last status: {status.status} | Persons: {status.total_persons} | Images: {status.total_images}
          </div>
        )}
        {message ? <div className="mt-3 text-sm">{message}</div> : null}
      </div>

      <div className="card">
        <h4 className="font-display mb-2">Training Logs</h4>
        <div className="space-y-2 max-h-[300px] overflow-auto text-sm">
          {logs.map((log) => (
            <div key={log.id} className="rounded border p-2">
              <div>{new Date(log.timestamp).toLocaleString()}</div>
              <div>Status: {log.status}</div>
              <div>Persons: {log.total_persons} | Images: {log.total_images}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
          <h4 className="font-display">Training Quality Audit</h4>
          <button
            type="button"
            className="rounded bg-ink text-white px-3 py-2 text-sm"
            onClick={refreshQuality}
            disabled={loadingQuality}
          >
            {loadingQuality ? "Refreshing..." : "Refresh Quality"}
          </button>
        </div>

        {quality ? (
          <>
            <div className="text-sm mb-3">
              Target Confidence: {Number(quality.target_confidence || 0).toFixed(2)} | Min Images/Person: {quality.min_images_per_person} |
              Ready: {quality.ready_persons}/{quality.total_persons} | Weak: {quality.weak_persons}
            </div>
            <div className="space-y-2 max-h-[320px] overflow-auto">
              {(quality.persons || []).map((person) => (
                <div key={person.person_id} className="rounded border p-3 text-sm bg-white">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="font-semibold">{person.name}</div>
                    <span
                      className={`text-xs px-2 py-1 rounded ${person.ready_for_high_confidence ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}
                    >
                      {person.ready_for_high_confidence ? "Ready for high confidence" : "Needs improvement"}
                    </span>
                  </div>
                  <div>Images: {person.total_images} | Encoded: {person.encoded_images} | Missing: {person.missing_encodings}</div>
                  <div>
                    Consistency: {person.embedding_consistency == null ? "N/A" : Number(person.embedding_consistency).toFixed(3)}
                  </div>
                  <div className="text-slate-600">Recommendation: {person.recommendation}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="text-sm">No quality report yet.</div>
        )}
      </div>

      <div className="card">
        <h4 className="font-display mb-2">Person Image Viewer</h4>
        <div className="flex flex-wrap items-end gap-3 mb-3">
          <label className="text-sm flex flex-col gap-1 min-w-[240px]">
            Person
            <select
              value={selectedPersonId || ""}
              onChange={(e) => setSelectedPersonId(Number(e.target.value) || null)}
              className="border rounded p-2"
            >
              <option value="">Select person</option>
              {persons.map((person) => (
                <option key={person.id} value={person.id}>
                  {person.name} ({person.department})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="rounded bg-ink text-white px-3 py-2"
            onClick={() => loadPersonImages(selectedPersonId)}
            disabled={!selectedPersonId || loadingImages}
          >
            {loadingImages ? "Loading..." : "Refresh Images"}
          </button>
        </div>

        {loadingImages ? <div className="text-sm">Loading images...</div> : null}
        {!loadingImages && selectedPersonId && personImages.length === 0 ? (
          <div className="text-sm">No images uploaded for this person.</div>
        ) : null}

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {personImages.map((img) => (
            <div key={img.id} className="rounded-lg border p-2 bg-white">
              {img.previewUrl ? (
                <img src={img.previewUrl} alt={`Person ${selectedPersonId} ${img.id}`} className="w-full h-32 object-cover rounded" />
              ) : (
                <div className="w-full h-32 rounded bg-slate-200 flex items-center justify-center text-xs text-slate-600">
                  Preview unavailable
                </div>
              )}
              <div className="text-xs mt-2">Image ID: {img.id}</div>
              <div className="text-xs text-slate-600">{new Date(img.uploaded_at).toLocaleString()}</div>
              <button
                type="button"
                className="mt-2 rounded bg-red-600 text-white px-2 py-1 text-xs"
                onClick={() => deletePersonImage(img.id)}
                disabled={deletingImageId === img.id}
              >
                {deletingImageId === img.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
