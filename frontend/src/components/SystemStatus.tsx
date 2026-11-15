import { useEffect, useState } from "react";
import { fetchHealth } from "../services/api";

export function SystemStatus() {
  const [label, setLabel] = useState("checking…");
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth().then((result) => {
      if (cancelled) {
        return;
      }
      setOk(result.ok);
      setLabel(result.label);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <span className={ok === true ? "status ok" : ok === false ? "status bad" : "status"}>
      {label}
    </span>
  );
}
