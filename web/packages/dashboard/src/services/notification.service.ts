import { Injectable } from "injection-js";
import { ArgsProps } from "antd/es/notification/interface";
import { Subject } from "rxjs";

@Injectable()
export class NotificationService {
  private notification$ = new Subject<{
    type?: "success" | "error" | "info" | "warning";
    args: ArgsProps;
  }>();

  private notificationDestroy$ = new Subject<string | number>();

  onNotification() {
    return this.notification$.asObservable();
  }

  onDestroyNotification() {
    return this.notificationDestroy$.asObservable();
  }

  error(args: ArgsProps): void {
    this.notification$.next({ type: "error", args });
  }

  success(args: ArgsProps): void {
    this.notification$.next({ type: "success", args });
  }

  info(args: ArgsProps): void {
    this.notification$.next({ type: "info", args });
  }

  warning(args: ArgsProps): void {
    this.notification$.next({ type: "warning", args });
  }

  open(args: ArgsProps): void {
    this.notification$.next({ args });
  }

  destroy(key: string | number): void {
    this.notificationDestroy$.next(key);
  }
}
