import { useState } from "react";

export default function ImageUploader({ onUpload, selectedPersonId, uploading }) {
  const [files, setFiles] = useState([]);

  const submit = async (event) => {
    event.preventDefault();
    if (files.length) {
      await onUpload(files);
      setFiles([]);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-3">
      <h3 className="font-display text-lg">Upload Reference Images</h3>
      <p className="text-sm text-slate-600">
        {selectedPersonId ? `Selected Person ID: ${selectedPersonId}` : "No person selected"}
      </p>
      <input
        type="file"
        accept="image/jpeg,image/png"
        multiple
        onChange={(event) => setFiles(Array.from(event.target.files || []))}
        className="block w-full rounded border p-2"
      />
      <button
        className="rounded-lg bg-accent text-white px-4 py-2 disabled:opacity-60"
        type="submit"
        disabled={uploading || !selectedPersonId || files.length === 0}
      >
        {uploading ? "Uploading..." : "Validate & Upload"}
      </button>
    </form>
  );
}
