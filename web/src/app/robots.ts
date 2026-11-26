import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/** Crawling stays open so search engines can read each page's `noindex`. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: new URL("/sitemap.xml", SITE_URL).toString(),
  };
}
