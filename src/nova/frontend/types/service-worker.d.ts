declare interface ExtendableEvent extends Event {
  waitUntil(promise: Promise<any>): void;
}

declare interface FetchEvent extends ExtendableEvent {
  request: Request;
  respondWith(response: Response | Promise<Response>): void;
}

declare interface SyncEvent extends ExtendableEvent {
  tag: string;
  lastChance: boolean;
}

declare interface PushEvent extends ExtendableEvent {
  data: PushMessageData;
}

declare interface NotificationEvent extends ExtendableEvent {
  action: string;
  notification: Notification;
}

declare interface ServiceWorkerGlobalScope {
  registration: ServiceWorkerRegistration;
  clients: Clients;
}

declare var self: ServiceWorkerGlobalScope;
