import { HTMLManager } from '@jupyter-widgets/html-manager';
import { ShinyComm } from './comm';

// TODO: when/how to inject a comm instance to the DOMModel options?
export class WidgetManager extends HTMLManager {
  // It seems the only place where this is relevant to us is in ManagerBase.set_state()
  // where a check for a model_id is made (to see if a comm exists), but the value isn't used
  // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/packages/base-manager/src/manager-base.ts#L671-L720
  _get_comm_info(): Promise<{}> {
    return Promise.resolve({model_id: "foo"});
  }

  _create_comm(
    comm_target_name: string,
    model_id: string,
    data?: any,
    metadata?: any,
    buffers?: ArrayBuffer[] | ArrayBufferView[]
  ): Promise<any> {
    console.log("_create_comm", comm_target_name, model_id, data, metadata, buffers);
    return Promise.resolve(new ShinyComm(model_id));
  }
}
