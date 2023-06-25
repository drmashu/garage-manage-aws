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
  command: string = '';
}

export const handler: Handler<HttpEvent, object> = async (event: HttpEvent, context:Context) => {
  // Log the event argument for debugging and for use in local development.
  console.log("start ControlLight " + event.pathParameters.garageId) ;

  const client = new IoTDataPlaneClient({ region: "ap-northeast-1" });

  if (event.pathParameters.command == 'on' || event.pathParameters.command == 'off') {
    const command = new PublishCommand({
      topic: event.pathParameters.garageId + "/light",
      payload: new TextEncoder().encode(event.pathParameters.command),
      payloadFormatIndicator: "UTF8_DATA",
      qos: 1,
      contentType: "text/plain",
    });
  
    const response = await client.send(command);  
    console.log("ControlLight response " + JSON.stringify(response));
    if (response.$metadata.httpStatusCode == 200) {
      console.log("ControlLight success.");
    } else {
      console.log("ControlLight failed.");
    }
  } else {
    console.log("ControlLight invalid command. : " + event.pathParameters.command);
  }
  return {};
};
