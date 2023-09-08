import { useEffect } from "react";
import { App } from "antd";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { useInject } from "@lepton-libs/di";

export const useSetupNotification = () => {
  const { notification } = App.useApp();
  const notificationService = useInject(NotificationService);

  useEffect(() => {
    const notificationSubscription = notificationService
      .onNotification()
      .subscribe((payload) => {
        switch (payload.type) {
          case "success":
            notification.success(payload.args);
            break;
          case "error":
            notification.error(payload.args);
            break;
          case "info":
            notification.info(payload.args);
            break;
          case "warning":
            notification.warning(payload.args);
            break;
          default:
            notification.open(payload.args);
            break;
        }
      });

    const destroySubscription = notificationService
      .onDestroyNotification()
      .subscribe((id) => {
        notification.destroy(id);
      });

    return () => {
      notificationSubscription.unsubscribe();
      destroySubscription.unsubscribe();
    };
  }, [notification, notificationService]);
};
