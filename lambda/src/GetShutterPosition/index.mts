import { Handler, Context } from "aws-lambda";
import { DynamoDBClient, DynamoDBClientConfig } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient,
  GetCommand,
} from '@aws-sdk/lib-dynamodb'
import { IoTDataPlaneClient, PublishCommand, PublishCommandInput, PayloadFormatIndicator } from '@aws-sdk/client-iot-data-plane'

const config: DynamoDBClientConfig = {};
const dbClient = new DynamoDBClient(config);
const documentClient = DynamoDBDocumentClient.from(dbClient);

class HttpEvent {
  pathParameters: PathParameters = new PathParameters();
}
class PathParameters {
  garageId: string = '';
}

export const handler: Handler<HttpEvent, object> = async (event: HttpEvent, context:Context) => {
  // Log the event argument for debugging and for use in local development.
  console.log("GetShutterPosition" + JSON.stringify(event, undefined, 2));


  const client = new IoTDataPlaneClient({ region: "ap-northeast-1" });
  const input = {
    topic: event.pathParameters.garageId + "/shutter", // required
    payload: new TextEncoder().encode("getPosition"),
    payloadFormatIndicator: PayloadFormatIndicator.UTF8_DATA,
    messageExpiry: 60,
  } as PublishCommandInput;
  const command = new PublishCommand(input);
  const response = await client.send(command);  
  return {};
};
