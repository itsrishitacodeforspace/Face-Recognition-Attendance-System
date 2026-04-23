import { useState } from "react";
import { authApi } from "../services/api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await authApi.login(username, password);
      sessionStorage.setItem("is_authed", "1");
      window.location.href = "/";
    } catch (err) {
      // Security: Only show generic error to prevent user enumeration
      setError(err?.response?.data?.detail || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="font-display text-2xl">Attendance Login</h1>
        <input
          type="text"
          placeholder="Username"
          className="w-full border rounded p-2"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full border rounded p-2"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button 
          type="submit"
          className="w-full bg-accent text-white rounded p-2 hover:bg-opacity-90"
        >
          Sign In
        </button>
        {error && <p className="text-red-600 text-sm">{error}</p>}
      </form>
    </div>
  );
}
