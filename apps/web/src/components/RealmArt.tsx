import Image from "next/image";

type Realm = "forest" | "ocean" | "mountain" | "tri-realm";

export function RealmArt({ realm, large = false }: { realm: Realm | string; large?: boolean }) {
  const kind = (["forest", "ocean", "mountain", "tri-realm"].includes(realm) ? realm : "tri-realm") as Realm;

  return <div className={`realm-art realm-art--${kind} realm-art--photographic${large ? " realm-art--large" : ""}`} aria-hidden="true">
    <Image className="realm-art__image" src={`/images/realm-${kind}.webp`} alt="" fill sizes="(max-width: 780px) calc(100vw - 36px), (max-width: 1304px) 50vw, 620px" />
  </div>;
}
