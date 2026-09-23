type Realm = "forest" | "ocean" | "mountain" | "tri-realm";

export function RealmArt({ realm, large = false }: { realm: Realm | string; large?: boolean }) {
  const kind = (["forest", "ocean", "mountain", "tri-realm"].includes(realm) ? realm : "tri-realm") as Realm;
  return <div className={`realm-art realm-art--${kind}${large ? " realm-art--large" : ""}`} aria-hidden="true">
    <span className="realm-art__orb" />
    <span className="realm-art__ring realm-art__ring--one" />
    <span className="realm-art__ring realm-art__ring--two" />
    {kind === "forest" && <svg viewBox="0 0 200 200" fill="none"><path d="M100 18 43 104h30l-28 43h37v31h36v-31h37l-28-43h30L100 18Z" stroke="currentColor" strokeWidth="2"/><path d="M100 62v117M72 105l28 26 28-26" stroke="currentColor" strokeWidth="2"/></svg>}
    {kind === "ocean" && <svg viewBox="0 0 200 200" fill="none"><path d="M22 96c25-24 49-24 75 0 25 24 50 24 81 0M22 126c25-24 49-24 75 0 25 24 50 24 81 0M22 156c25-24 49-24 75 0 25 24 50 24 81 0" stroke="currentColor" strokeWidth="2"/><circle cx="100" cy="61" r="25" stroke="currentColor" strokeWidth="2"/></svg>}
    {kind === "mountain" && <svg viewBox="0 0 200 200" fill="none"><path d="m20 155 58-100 35 61 20-32 47 71H20Z" stroke="currentColor" strokeWidth="2"/><path d="m65 78 13 21 13-21m28 20 14 20 14-20" stroke="currentColor" strokeWidth="2"/><path d="M30 170h140" stroke="currentColor" strokeWidth="2"/></svg>}
    {kind === "tri-realm" && <svg viewBox="0 0 200 200" fill="none"><path d="M78 30h44M86 30v32l-33 78c-9 20 2 34 23 34h48c21 0 32-14 23-34l-33-78V30" stroke="currentColor" strokeWidth="2"/><path d="M62 132c28-12 49 17 76 2M79 113l21-31 21 31" stroke="currentColor" strokeWidth="2"/><circle cx="100" cy="60" r="5" fill="currentColor"/></svg>}
  </div>;
}
