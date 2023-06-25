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
  console.log("start RequestGarageState " + event.pathParameters.garageId) ;

  const client = new IoTDataPlaneClient({ region: "ap-northeast-1" });

  const command = new PublishCommand({
    topic: event.pathParameters.garageId + "/shutter",
    payload: new TextEncoder().encode("update"),
    payloadFormatIndicator: "UTF8_DATA",
    qos: 1,
    contentType: "text/plain",
  });

  const response = await client.send(command);  
  console.log("RequestGarageState response " + JSON.stringify(response));
  if (response.$metadata.httpStatusCode == 200) {
    console.log("RequestGarageState success.");
  } else {
    console.log("RequestGarageState failed.");
  }
  return {};
};
