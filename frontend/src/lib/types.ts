export type Role = "visitor" | "supplier";
export type ListingType = "rent" | "sale";
export type RentalPeriod = "hour" | "day" | "week" | "month" | "none";
export type ProductStatus = "pending" | "approved" | "rejected";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface UserPublic {
  id: number;
  full_name: string;
  avatar: string | null;
  role: Role;
  created_at: string;
}

export interface Me {
  id: number;
  phone: string;
  first_name: string;
  last_name: string;
  email: string;
  gender: "M" | "F" | "X" | "";
  birth_date: string | null;
  avatar: string | null;
  role: Role;
  is_phone_verified: boolean;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  order: number;
  parent: number | null;
  children: Category[];
  /** Own attributes plus those inherited from the parent category. */
  attributes: CategoryAttribute[];
}

export interface SupplierPublic {
  id: number;
  user: UserPublic;
  city: string;
  bio: string;
  is_verified: boolean;
  rating_avg: string;
  products_count: number;
  phone: string | null;
  whatsapp_number: string | null;
  created_at: string;
}

export type LocationPrecision = "exact" | "approximate";

export interface ProductImage {
  id: number;
  image: string;
  is_cover: boolean;
  order: number;
  width: number;
  height: number;
}

export type AttributeType = "text" | "number" | "boolean" | "select" | "multi_select" | "date";

export interface CategoryAttribute {
  id: number;
  name: string;
  slug: string;
  attribute_type: AttributeType;
  required: boolean;
  filterable: boolean;
  searchable: boolean;
  unit: string;
  options: string[];
  position: number;
}

export type AttributeValue = string | number | boolean | string[];

export interface ProductAttribute {
  slug: string;
  name: string;
  attribute_type: AttributeType;
  unit: string;
  value: AttributeValue;
}

export interface ProductListItem {
  id: number;
  title: string;
  slug: string;
  category: string | null; // category slug
  price: string;
  currency: string;
  listing_type: ListingType;
  rental_period: RentalPeriod;
  city: string;
  cover_image: string | null;
  views_count: number;
  shares_count: number;
  supplier_name: string;
  status: ProductStatus;
  is_active: boolean;
  is_favorite: boolean;
  created_at: string;
}

export interface Favorite {
  id: number;
  product: ProductListItem;
  created_at: string;
}

export interface ProductDetail extends Omit<ProductListItem, "category"> {
  description: string;
  supplier: SupplierPublic;
  images: ProductImage[];
  published_at: string | null;
  category: Category | null;
  location: string;
  region: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  location_precision: LocationPrecision;
  map_url: string | null;
  attributes: ProductAttribute[];
}

export interface ProductWritePayload {
  title: string;
  category: number;
  description: string;
  price: number;
  currency: string;
  listing_type: ListingType;
  rental_period: RentalPeriod;
  city: string;
  location?: string;
  region?: string;
  country?: string;
  latitude?: number | null;
  longitude?: number | null;
  place_id?: string;
  location_precision?: LocationPrecision;
}

export interface ConversationSummary {
  id: number;
  other_participant: UserPublic;
  initial_product: ProductListItem | null;
  last_message: { body: string; created_at: string; is_mine: boolean } | null;
  unread_count: number;
  updated_at: string;
}

export type MessageType = "text" | "audio" | "image" | "video" | "product" | "system";

export type AttachmentKind = "image" | "video" | "audio";
export type AttachmentStatus = "uploading" | "processing" | "ready" | "failed";

export interface MessageAttachment {
  id: number;
  kind: AttachmentKind;
  status: AttachmentStatus;
  /** Served by the API, never a storage URL: conversations are private. */
  url: string;
  /** Thumbnail for an image, still frame for a video. */
  poster_url: string | null;
  mime_type: string;
  size: number;
  width: number;
  height: number;
  duration: number;
}

export interface Message {
  id: number;
  conversation: number;
  sender: UserPublic;
  message_type: MessageType;
  body: string;
  shared_product: ProductListItem | null;
  attachments: MessageAttachment[];
  created_at: string;
  read_at: string | null;
  is_mine: boolean;
}

export type NotificationType =
  | "new_message"
  | "new_product"
  | "product_updated"
  | "product_approved"
  | "product_rejected"
  | "favorite"
  | "live_started"
  | "system";

export interface AppNotification {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  url: string;
  data: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface SupplierStats {
  products_online: number;
  products_total: number;
  total_views: number;
  total_shares: number;
  total_contacts: number;
  unread_messages: number;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface SupplierAnalytics {
  days: number;
  views: SeriesPoint[];
  contacts: SeriesPoint[];
  messages: SeriesPoint[];
  products_breakdown: {
    online: number;
    unpublished: number;
    pending: number;
    rejected: number;
  };
  top_products: Array<{
    id: number;
    title: string;
    slug: string;
    views_count: number;
    shares_count: number;
  }>;
  top_categories: Array<{ name: string; slug: string; products: number }>;
}

export type LiveStatus = "draft" | "scheduled" | "live" | "ended" | "cancelled";

export interface LiveProductEntry {
  id: number;
  product: ProductListItem;
  position: number;
  is_featured: boolean;
  started_at: string | null;
  ended_at: string | null;
}

export interface LiveSession {
  id: number;
  host: UserPublic;
  title: string;
  description: string;
  status: LiveStatus;
  thumbnail: string | null;
  scheduled_for: string | null;
  started_at: string | null;
  ended_at: string | null;
  peak_viewers: number;
  current_viewers: number;
  provider: string;
  playback_url: string;
  live_products: LiveProductEntry[];
  created_at: string;
}

export interface ProductFiltersQuery {
  search?: string;
  category?: string;
  city?: string;
  listing_type?: ListingType;
  price_min?: string;
  price_max?: string;
  ordering?: string;
  page?: string;
  mine?: "true";
  favorites?: "true";
  /** Dynamic per-category attribute filters, e.g. { attr_carburant: "Diesel" } */
  attributes?: Record<string, string>;
}
