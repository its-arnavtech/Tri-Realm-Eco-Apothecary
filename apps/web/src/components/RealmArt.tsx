import Image from "next/image";

type Realm = "forest" | "ocean" | "mountain" | "tri-realm";

export function RealmArt({ realm, large = false }: { realm: Realm | string; large?: boolean }) {
  const kind = (["forest", "ocean", "mountain", "tri-realm"].includes(realm) ? realm : "tri-realm") as Realm;

  if (kind !== "tri-realm") {
    return <div className={`realm-art realm-art--${kind} realm-art--photographic${large ? " realm-art--large" : ""}`} aria-hidden="true">
      <Image className="realm-art__image" src={`/images/realm-${kind}.webp`} alt="" fill sizes="(max-width: 780px) calc(100vw - 36px), (max-width: 1304px) 50vw, 620px" />
    </div>;
  }

  return <div className={`realm-art realm-art--${kind}${large ? " realm-art--large" : ""}`} aria-hidden="true">
    <span className="realm-art__orb" />
    <span className="realm-art__ring realm-art__ring--one" />
    <span className="realm-art__ring realm-art__ring--two" />
    <svg viewBox="0 0 200 200" fill="none"><path d="M78 30h44M86 30v32l-33 78c-9 20 2 34 23 34h48c21 0 32-14 23-34l-33-78V30" stroke="currentColor" strokeWidth="2"/><path d="M62 132c28-12 49 17 76 2M79 113l21-31 21 31" stroke="currentColor" strokeWidth="2"/><circle cx="100" cy="60" r="5" fill="currentColor"/></svg>
  </div>;
}
