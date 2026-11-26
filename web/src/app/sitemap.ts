import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/** Only the home page is indexable: everything else is behind the login. */
export default function sitemap(): MetadataRoute.Sitemap {
  return [{ url: new URL("/", SITE_URL).toString() }];
}
